from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from ..models import Order,Invoice,OrderProgress,OrderPayment,Expense,OrderItem,LensStock  # Import LensStock for on_hold handling
from ..serializers import OrderPaymentSerializer
from ..services.order_payment_service import OrderPaymentService  # Assuming service function is in OrderService

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
            
            # ✅ Handle on_hold status change with lens stock management
            if on_hold is not None:
                previous_on_hold = order.on_hold
                new_on_hold = on_hold
                
                print(f"\n=== ON_HOLD PAYMENT UPDATE - Order #{order.pk} ===")
                print(f"Previous on_hold: {previous_on_hold}")
                print(f"New on_hold: {new_on_hold}")
                
                # Detect transitions
                transitioning_off_hold = previous_on_hold and not new_on_hold  # True → False
                transitioning_to_hold = not previous_on_hold and new_on_hold   # False → True
                
                if transitioning_off_hold:
                    # Transitioning from on_hold=True to False: deduct lens stock
                    print("[PAYMENT] Transitioning OFF hold - deducting lens stock")
                    
                    # Get all lens items for this order
                    lens_items = OrderItem.objects.filter(
                        order=order,
                        is_deleted=False,
                        lens__isnull=False
                    )
                    
                    for lens_item in lens_items:
                        lens_stock = LensStock.objects.select_for_update().filter(
                            lens=lens_item.lens,
                            branch=order.branch
                        ).first()
                        
                        if lens_stock:
                            if lens_stock.qty < lens_item.quantity:
                                raise ValueError(f"Insufficient lens stock for lens ID {lens_item.lens.id}")
                            print(f"[PAYMENT] Deducting lens {lens_item.lens.id}: qty {lens_stock.qty} → {lens_stock.qty - lens_item.quantity}")
                            lens_stock.qty -= lens_item.quantity
                            lens_stock.save()
                        else:
                            raise ValueError(f"Lens stock not found for lens ID {lens_item.lens.id}")
                            
                elif transitioning_to_hold:
                    # Transitioning from on_hold=False to True: restore lens stock
                    print("[PAYMENT] Transitioning TO hold - restoring lens stock")
                    
                    # Get all lens items for this order
                    lens_items = OrderItem.objects.filter(
                        order=order,
                        is_deleted=False,
                        lens__isnull=False
                    )
                    
                    for lens_item in lens_items:
                        lens_stock = LensStock.objects.select_for_update().filter(
                            lens=lens_item.lens,
                            branch=order.branch
                        ).first()
                        
                        if lens_stock:
                            print(f"[PAYMENT] Restoring lens {lens_item.lens.id}: qty {lens_stock.qty} → {lens_stock.qty + lens_item.quantity}")
                            lens_stock.qty += lens_item.quantity
                            lens_stock.save()
                
                # Update on_hold status after stock adjustments
                order.on_hold = new_on_hold
                order.save(update_fields=['on_hold'])
                print(f"=== ON_HOLD PAYMENT UPDATE END ===\n")

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
