from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from ..models import Order,Invoice,OrderProgress  # Assuming Order model exists
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
            total_payment = OrderPaymentService.update_process_payments(order, payments_data,admin_id,user_id)

            # ✅ Return updated order payment details
            updated_payments = order.orderpayment_set.all()
            response_serializer = OrderPaymentSerializer(updated_payments, many=True)
            
            return Response({
                "message": "Payments updated successfully.",
                "total_payment": total_payment,
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
