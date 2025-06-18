from django.db import transaction
from rest_framework import status,permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import Order, ArrivalStatus, OrderProgress,RefractionDetails,Refraction
from ..serializers import OrderSerializer,ArrivalStatusBulkCreateSerializer,OrderProgressSerializer
from ..services.order_payment_service import OrderPaymentService
from ..services.stock_validation_service import StockValidationService
from ..services.order_service import OrderService
from ..services.patient_service import PatientService
from ..services.Invoice_service import InvoiceService
from ..services.refraction_details_service import RefractionDetailsService
from django.utils import timezone
from django.shortcuts import get_object_or_404
from ..services.soft_delete_service import OrderSoftDeleteService
# from ..services.order_payment_service import refund_order  # adjust as needed
from rest_framework.exceptions import ValidationError

class OrderCreateView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            # Start transaction
            with transaction.atomic():
                
                # 🔹 Step 1: Validate & Create/Update Patient
                patient_data = request.data.get("patient")
                if not patient_data:
                    return Response({"error": "Patient details are required."}, status=status.HTTP_400_BAD_REQUEST)

                patient = PatientService.create_or_update_patient(patient_data)

                # 🔹 Step 2: Update Refraction linkage if provided
                refraction_id = patient_data.get("refraction_id")
                if refraction_id:
                    try:
                        refraction = Refraction.objects.get(id=refraction_id)
                        refraction.patient = patient
                        refraction.save()
                    except Refraction.DoesNotExist:
                        return Response({"error": "Refraction record not found."}, status=status.HTTP_400_BAD_REQUEST)

                # 🔹 Step 3: Create Refraction Details if provided
                refraction_details_data = request.data.get("refraction_details")
                if refraction_details_data:
                    refraction_details_data["patient"] = patient.id
                    RefractionDetailsService.create_refraction_details(refraction_details_data)
                else:
                    if patient.refraction_id:
                        try:
                            refraction_details = RefractionDetails.objects.get(refraction_id=patient.refraction_id)
                            refraction_details.patient_id = patient.id
                            refraction_details.save()
                        except RefractionDetails.DoesNotExist:
                            pass  # No existing refraction details, continue

                # 🔹 Step 4: Extract Order Data
                order_data = request.data.get('order')
                if not order_data:
                    return Response({"error": "The 'order' field is required."}, status=status.HTTP_400_BAD_REQUEST)
                
                # ✅ Ensure order_date is set
                if not order_data.get('user_date'):
                    order_data['user_date'] = timezone.now().date()

                # Add customer ID to order data
                order_data["customer"] = patient.id
                
                # Get order items
                order_items_data = request.data.get('order_items', [])
                
                # 🔹 Step 5: Create Order + Items using the updated service
                # The stock validation and adjustment is now handled within create_order
                # based on the on_hold status
                order = OrderService.create_order(order_data, order_items_data)

                # 🔹 Step 6: Generate Invoice
                InvoiceService.create_invoice(order)

                # 🔹 Step 7: Create Payments
                payments_data = request.data.get('order_payments', [])
                if not payments_data:
                    raise ValueError("At least one order payment is required.")

                total_payment = OrderPaymentService.process_payments(order, payments_data)

                # 🔹 Step 8: Validate payment amount
                if total_payment > order.total_price:
                    raise ValueError("Total payments exceed the order total price.")
                
                response_serializer = OrderSerializer(order)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class OrderSoftDeleteView(APIView):
    """
    Soft deletes an order and cascades to related records.
    """

    def delete(self, request, order_id):
        order = get_object_or_404(Order.all_objects, id=order_id)

        if order.is_deleted:
            return Response({"detail": "Order already deleted."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason", "No reason provided.")
        deleted_by = request.user if request.user.is_authenticated else None

        OrderSoftDeleteService.soft_delete_order(order_id=order.id, deleted_by=deleted_by, reason=reason)

        return Response({"detail": "Order soft-deleted successfully."}, status=status.HTTP_200_OK)
    
class OrderRefundView(APIView):
    def post(self, request, pk):
        expense_data = request.data

        try:
            result = OrderPaymentService.refund_order(order_id=pk, expense_data=expense_data)
            return Response(result, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Refund failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderProgressStatusListView(APIView):
    def get(self, request):
        order_id = request.query_params.get('order_id')
        qs = OrderProgress.objects.all()
        if order_id:
            qs = qs.filter(order_id=order_id)
        # Always order by changed_at for timeline clarity
        qs = qs.order_by('-changed_at')
        return Response(OrderProgressSerializer(qs, many=True).data)



class ArrivalStatusBulkCreateView(APIView):
    """
    Bulk-mark orders as 'recived' (arrival confirmed).

    Payload:
        {"order_ids": [12, 15, 18]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ArrivalStatusBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order_ids = ser.validated_data["order_ids"]
        now = timezone.now()

        # --- 1. Fetch & sanity-check orders -------------------------------
        orders_qs = (
            Order.objects
            .filter(id__in=order_ids, is_deleted=False)
            .only("id")                           # small query
        )
        found_ids = set(orders_qs.values_list("id", flat=True))
        missing   = set(order_ids) - found_ids
        if missing:
            return Response(
                {"error": f"Order(s) not found or deleted: {sorted(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 2. Skip orders already marked as received --------------------
        # Get latest status for each order
        latest_statuses = {}
        for oid in order_ids:
            latest_status = (
                ArrivalStatus.objects
                .filter(order_id=oid)
                .order_by('-created_at')
                .first()
            )
            latest_statuses[oid] = latest_status

        # Create new arrival statuses only for orders that don't have 'recived' status
        to_create = []
        already_received = []
        
        for oid in order_ids:
            latest_status = latest_statuses[oid]
            if latest_status and latest_status.arrival_status == 'recived':
                already_received.append(oid)
            else:
                to_create.append(ArrivalStatus(
                    order_id=oid,
                    arrival_status='recived',
                    created_at=now,
                ))

        # Create all new arrival statuses in one bulk operation
        if to_create:
            ArrivalStatus.objects.bulk_create(to_create)

        return Response({
            "created": len(to_create),
            "already_received": already_received,
            "timestamp": now.isoformat()
        })