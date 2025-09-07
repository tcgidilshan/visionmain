from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from ..services.patient_service import PatientService
from ..models import Patient, SolderingOrder, Branch,SolderingInvoice,SolderingPayment
from ..serializers import SolderingOrderSerializer, SolderingInvoiceSerializer, SolderingPaymentSerializer
from ..services.soldering_order_service import SolderingOrderService
from ..services.soldering_payment_service import SolderingPaymentService
from ..services.soldering_invoice_service import SolderingInvoiceService
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from ..services.pagination_service import PaginationService
from ..serializers import SolderingPaymentSerializer,SolderingOrderSerializer
from django.utils.dateparse import parse_date

class CreateSolderingOrderView(APIView):
    permission_classes = [IsAuthenticated]
    @transaction.atomic
    def post(self, request):
        data = request.data

        # 1. Validate required fields
        required_fields = ['patient_id', 'branch_id', 'price', 'payments']
        for field in required_fields:
            if field not in data:
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 2. Hfind patient
            patient_id = data.get("patient_id")
            if not patient_id:
                    return Response({"error": "Patient details are required."}, status=status.HTTP_400_BAD_REQUEST)
            patient = None
            if patient_id:
                    try:
                        patient = Patient.objects.get(id=patient_id)
                    except Patient.DoesNotExist:
                        raise ValueError("Patient with the provided ID does not exist.")
            else:
                    raise ValueError("Patient ID is required.")

            # 3. Get branch
            branch = get_object_or_404(Branch, id=data['branch_id'])

            # 4. Create order
            order = SolderingOrderService.create_order(
                patient=patient,
                branch=branch,
                price=Decimal(str(data['price'])),
                note=data.get('note', ''),
                progress_status=data.get('progress_status', SolderingOrder.ProgressStatus.RECEIVED_FROM_CUSTOMER),
            )

            # 5. Process payments (mandatory)
            payments = SolderingPaymentService.process_solder_payments(order, data['payments'])

            # 6. Generate invoice
            invoice = SolderingInvoiceService.create_invoice(order)

            # 7. Return all results
            return Response({
                "order": SolderingOrderSerializer(order).data,
                "invoice": SolderingInvoiceSerializer(invoice).data,
                "payments": SolderingPaymentSerializer(payments, many=True).data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to create order: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SolderingOrderProgressUpdateView(APIView):
    # Optionally restrict this endpoint for staff/admin roles only
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        order = get_object_or_404(SolderingOrder, pk=pk, is_deleted=False)
        new_progress_status = request.data.get('progress_status')

        # Validate progress_status
        valid_choices = [choice[0] for choice in SolderingOrder.ProgressStatus.choices]
        if new_progress_status not in valid_choices:
            return Response({"error": "Invalid progress status."}, status=status.HTTP_400_BAD_REQUEST)

        # Update only the progress_status
        order.progress_status = new_progress_status
        order.save()  # Will trigger progress_status_updated_at auto-update as per your model

        return Response({
            "order": SolderingOrderSerializer(order).data,
            "message": f"Progress status updated to '{order.get_progress_status_display()}'.",
            "progress_status_updated_at": order.progress_status_updated_at
        }, status=status.HTTP_200_OK)

class SolderingInvoiceSearchView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SolderingInvoiceSerializer
    pagination_class = PaginationService

    def get_queryset(self):
        queryset = SolderingInvoice.objects.filter(is_deleted=False)
        invoice_number = self.request.query_params.get('invoice_number')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        patient_mobile = self.request.query_params.get('mobile')
        progress_status = self.request.query_params.get('progress_status')
        branch_id = self.request.query_params.get('branch_id')
        nic = self.request.query_params.get('nic')

        if invoice_number:
            queryset = queryset.filter(invoice_number__icontains=invoice_number)
        if start_date:
            try:
                start = parse_date(start_date)
                if start:
                    queryset = queryset.filter(invoice_date__gte=start)
            except Exception:
                pass  # Optional: log error
        if end_date:
            try:
                end = parse_date(end_date)
                if end:
                    queryset = queryset.filter(invoice_date__lte=end)
        
            except Exception:
                pass  # Optional: log error
        if patient_mobile:
            # Join through order__patient__phone_number (assuming field name)
            queryset = queryset.filter(order__patient__phone_number__icontains=patient_mobile)
        if progress_status:
            queryset = queryset.filter(order__progress_status=progress_status)
        if branch_id:
            queryset = queryset.filter(order__branch_id=branch_id)
        if nic:
            queryset = queryset.filter(order__patient__nic__icontains=nic)
        queryset = queryset.order_by('-invoice_date', '-id')
        return queryset

    def list(self, request, *args, **kwargs):
        """Override to provide error messages for invalid dates if needed."""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": "Invalid query parameters."}, status=status.HTTP_400_BAD_REQUEST)

class SolderingOrderEditView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        order = get_object_or_404(SolderingOrder, pk=pk, is_deleted=False)
        data = request.data

        # --- Only update allowed fields ---
        allowed_fields = ['price', 'note', 'progress_status']
        for field in allowed_fields:
            if field in data:
                setattr(order, field, data[field])

        # Handle branch update (if using branch_id in request)
        branch_id = data.get('branch_id')
        if branch_id:
            branch = Branch.objects.filter(id=branch_id).first()
            if not branch:
                return Response({"error": "Branch not found."}, status=400)
            order.branch = branch

        order.save()

        # --- Payment Handling ---
        payments_data = data.get("payments")
        if payments_data is not None:
            try:
                # You may want to pass admin_id/user_id from request.user if available
                admin_id = getattr(request.user, "id", None)
                user_id = getattr(request.user, "id", None)
                total_paid = SolderingPaymentService.append_on_change_payments_for_order(
                    order, payments_data, admin_id, user_id
                )
            except ValidationError as e:
                transaction.set_rollback(True)
                return Response({"error": str(e)}, status=400)
            except Exception as e:
                transaction.set_rollback(True)
                return Response({"error": f"Payment update failed: {str(e)}"}, status=400)

        # --- Output full, up-to-date order ---
        return Response(SolderingOrderSerializer(order).data, status=status.HTTP_200_OK)