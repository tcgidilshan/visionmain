from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from ..models import Order,ExternalLens,Invoice, CustomUser,OrderItemWhatsAppLog,OrderProgress,ArrivalStatus, OrderFeedback
from ..serializers import OrderSerializer,ExternalLensSerializer
from ..services.order_service import OrderService
from ..services.audit_log_service import OrderAuditLogService
from ..services.patient_service import PatientService
from ..services.external_lens_service import ExternalLensService
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from ..services.mnt_order_service import MntOrderService

class OrderUpdateView(APIView):
    """
    API View to update an existing order, including external lenses, stock validation, and payments.
    """

    @transaction.atomic
    def put(self, request, pk, *args, **kwargs):
        try:
            order = Order.objects.get(pk=pk)
            admin_id = request.data.get("admin_id")
            user_id = request.data.get("user_id")
            if not admin_id:
               return Response({"error": "Admin ID is required to perform an Edit operation."}, status=status.HTTP_400_BAD_REQUEST)
            # Step 1: Update Patient Details (if provided)
            #//!no need patient service frontend architecher send direct patint ID
            # patient_data = request.data.get("patient")
            # if patient_data:
            #     PatientService.create_or_update_patient(patient_data)


            # Step 2: Extract Order Data (check if on_hold status is changing)
            order_data = request.data.get("order", {})
            order_items_data = request.data.get("order_items", [])
            payments_data = request.data.get("order_payments", [])
            co_order = request.data.get("co_order")
            co_note = request.data.get("co_note","")
            

            # Check if we're changing on_hold status
            current_on_hold = order.on_hold
            new_on_hold = order_data.get("on_hold", current_on_hold)
            original_order_data = {
            field: getattr(order, field)
            for field in OrderAuditLogService.TRACKED_FIELDS
            }
            # Log the on-hold transition if it's happening (can be helpful for debugging)
            if current_on_hold != new_on_hold:
                print(f"Order {order.id} on_hold status changing: {current_on_hold} → {new_on_hold}")
            
            # Step 3: Update Order 
            # The updated update_order method now handles different stock behavior based on on_hold status and refunds
            updated_order = OrderService.update_order(order, order_data, order_items_data, payments_data, admin_id, user_id)
            
            # Now log only if update succeeded
            OrderAuditLogService.log_order_changes(
            order_instance=updated_order,
            updated_data=order_data,
            original_data=original_order_data,
            raw_data={
                "admin_id": admin_id,
                "user_id": user_id
            }
            )
              # --- MNT logic (if requested) ---
            if request.data.get("mnt", False):
                admin_id = request.data.get("admin_id")
                admin = CustomUser.objects.get(pk=admin_id) if admin_id else None

                # Business/medical validation: Only allow MNT for eligible orders (e.g., factory)
                if not MntOrderService.is_mnt_allowed(updated_order):
                    return Response({"error": "MNT can only be created for factory orders."}, status=400)

                # Prevent duplicate MNT for same order/branch in same request/session (optional)
                # (Could also use unique_together constraint at DB/model level)
                existing = MntOrderService.get_latest_mnt_order_for_order(updated_order)
                # If you want to block multiple MNT in rapid succession, check time window or manual status

                # Actually create the MNT order
                #progress stage
                
                mnt_order = MntOrderService.create_mnt_order(
                    order=updated_order,
                    mnt_price=request.data.get("mnt_price"),
                    user_id=request.data.get("user_id"),
                    admin_id=request.data.get("admin_id"),
                )
                OrderItemWhatsAppLog.objects.create(
                    order=updated_order,
                    status="Mnt Marked",
                    created_at=timezone.now()
                )
                ArrivalStatus.objects.create(
                    order=updated_order,
                    arrival_status="Mnt Marked",
                    created_at=timezone.now()
                )
                #check relavent order id alast progress status of it not received_from_customer
                last_progress = OrderProgress.objects.filter(order=updated_order).order_by('-id').first()
                if last_progress and last_progress.progress_status != "received_from_customer":
                    OrderProgress.objects.create(
                        order=updated_order,
                        progress_status="received_from_customer",
                        created_at=timezone.now()
                    )
                # Optionally: return mnt_order info in response or audit log

            if co_order is not None:
                updated_order.co_order = co_order
                updated_order.co_note = co_note
                updated_order.save()   


            # Step 5: Return Updated Order Response
            response_serializer = OrderSerializer(updated_order)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except ExternalLens.DoesNotExist:
            return Response({"error": "External lens not found."}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            transaction.set_rollback(True)
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderUpdateFitStatusView(APIView):
    """
    API View to update the fit status of an order.
    """

    @transaction.atomic
    def put(self, request, pk, *args, **kwargs):
        try:
            order = Order.objects.get(pk=pk)
            order.fitting_status = request.data.get("fitting_status")
            order.save()
            return Response({"message": "Order fit status updated successfully."}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderDeliveryMarkView(APIView):
    """
    Mark order as delivered to customer.
    Expects: invoice_number, user_code, password in POST body.
    """
    def post(self, request):
        invoice_number = request.data.get('invoice_number')
        user_code = request.data.get('user_code')
        password = request.data.get('password')

        if not invoice_number or not user_code or not password:
            return Response({'detail': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate user
        try:
            user = CustomUser.objects.get(user_code=user_code)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)

        #Prevent inactive users from marking as delivered 
        if not user.is_active:
            return Response({'detail': 'User account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)

        if not user.check_password(password):
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the order by invoice number
        try:
            invoice = Invoice.objects.get(invoice_number=invoice_number)
            order = invoice.order
        except Invoice.DoesNotExist:
            return Response({'detail': 'Invalid invoice number.'}, status=status.HTTP_400_BAD_REQUEST)

        # Soft-delete check (highly recommended for medical systems)
        if hasattr(order, 'is_deleted') and order.is_deleted:
            return Response({'detail': 'Order has been deleted.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.issued_by:
            return Response({'detail': 'This order is already marked as delivered.'}, status=status.HTTP_400_BAD_REQUEST)

        # Mark as delivered
        order.issued_by = user
        order.issued_date = timezone.now()
        order.save()

        # Check if feedback exists for this order with null user and update it
        feedback = OrderFeedback.objects.filter(order=order, user__isnull=True).first()
        if feedback:
            feedback.user = user
            feedback.save(update_fields=['user'])

        return Response({'detail': 'Order marked as delivered.', 'order_id': order.id}, status=status.HTTP_200_OK)

        for item_id, deleted_item in existing_items.items():
            if item_id not in updated_item_ids:
                # ...restock logic...
                deleted_item.delete()