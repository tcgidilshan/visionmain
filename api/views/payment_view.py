from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from ..models import Order,Invoice,OrderProgress,OrderPayment,Expense,OrderItem,LensStock,LensCleanerStock,OtherItemStock,HearingItemStock  # Assuming Order model exists
from ..serializers import OrderPaymentSerializer
from ..services.order_payment_service import OrderPaymentService  # Assuming service function in OrderService
from ..services.stock_validation_service import StockValidationService

class PaymentView(APIView):
    """
    API View to update payments for an existing order based on order ID or invoice ID.
    """

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        order_id = request.data.get("order_id")  # Order ID from request
        progress_status = request.data.get("progress_status")
        on_hold = request.data.get("on_hold")
        invoice_id = request.data.get("invoice_id")  # Invoice ID (if used)
        payments_data = request.data.get("payments", [])  # List of payments
        admin_id = request.data.get("admin_id")
        user_id = request.data.get("user_id")

        if not order_id and not invoice_id:
            return Response({"error": "Order ID or Invoice ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ✅ Fetch order using order_id or invoice_id
            order = None
            if order_id:
                order = Order.objects.get(id=order_id)
            elif invoice_id:
                order = Order.objects.get(invoice_id=invoice_id)

            # Track on_hold flag changes (same pattern as order_service.py)
            was_on_hold = order.on_hold
            will_be_on_hold = on_hold if on_hold is not None else was_on_hold
            # Detect transition from on-hold to active
            transitioning_off_hold = was_on_hold and not will_be_on_hold

            # If transitioning from on-hold to active, validate lens stock
            lens_stock_updates = []
            if transitioning_off_hold:
                branch_id = order.branch_id
                if not branch_id:
                    raise ValueError("Order is not associated with a branch.")

                # Get ALL lens items from existing order items for validation
                # Only reduce stock for lens items when transitioning from on_hold=True to on_hold=False
                lens_items = []
                for existing_item in order.order_items.filter(is_deleted=False):
                    if existing_item.lens and not existing_item.is_non_stock:
                        # Convert existing item to item_data format for validation
                        lens_items.append({
                            'id': existing_item.id,
                            'lens': existing_item.lens_id,
                            'quantity': existing_item.quantity,
                            'is_non_stock': existing_item.is_non_stock
                        })
                
                # Only validate if there are actual stock items to validate
                if lens_items:
                    _, lens_stock_updates = StockValidationService.validate_stocks(
                        lens_items, branch_id, on_hold=False
                    )

            # 1. Update the progress_status field (capture previous if needed)
            incoming_status = request.data.get('progress_status', None)
            last_progress = order.order_progress_status.order_by('-changed_at').first()
            # Always log if this is the first status, or if it's different from the last logged status
            if incoming_status and (
                last_progress is None or last_progress.progress_status != incoming_status
            ):
                OrderProgress.objects.create(
                    order=order,
                    progress_status=incoming_status,
                )
            

            if not payments_data:
                return Response({"error": "Payments data is required."}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Process payments using the service function
            total_payment = OrderPaymentService.append_on_change_payments_for_order(order, payments_data,admin_id,user_id)

            # ✅ Update order.total_payment = sum(OrderPayments) - sum(Expenses)
            total_payments = OrderPayment.objects.filter(
                order=order,
                is_deleted=False
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            total_expenses = Expense.objects.filter(
                order_refund=order
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            order.total_payment = total_payments - total_expenses
            order.save(update_fields=['total_payment'])
            #update on_hold status
            if on_hold is not None:
                order.on_hold = on_hold
                order.save(update_fields=['on_hold'])

            # Final: Deduct lens stock if on_hold → False (same pattern as order_service.py)
            if transitioning_off_hold:
                StockValidationService.adjust_stocks(lens_stock_updates)

            # ✅ Return updated order payment details
            updated_payments = order.orderpayment_set.all()
            response_serializer = OrderPaymentSerializer(updated_payments, many=True)
            
            return Response({
                "message": "Payments updated successfully.",
                "total_payment": float(order.total_payment),
                "balance": float(order.total_price - order.total_payment),
                "updated_payments": response_serializer.data
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get(self, request, *args, **kwargs):
        order_id = request.query_params.get("order_id")
        invoice_id = request.query_params.get("invoice_id")

        if not order_id and not invoice_id:
            return Response({"error": "Order ID or Invoice ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        response = OrderPaymentService.get_payments(order_id, invoice_id)

        if "error" in response:
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        return Response(response, status=status.HTTP_200_OK)
