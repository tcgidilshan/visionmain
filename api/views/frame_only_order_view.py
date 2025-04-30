from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import FrameOnlyOrderSerializer
from ..services.frame_only_order_service import FrameOnlyOrderService
from ..services.order_payment_service import OrderPaymentService
from django.db import transaction
from ..serializers import OrderSerializer  # Optional if you want to return full order
from decimal import Decimal
from datetime import date

class FrameOnlyOrderCreateView(APIView):
    """
    Creates a Frame-Only Factory Order.
    """

    def post(self, request, *args, **kwargs):
        serializer = FrameOnlyOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                # ✅ FrameOnlyOrderService will now create or reuse the patient
                order = FrameOnlyOrderService.create(serializer.validated_data)

                # Handle payments
                payments_data = request.data.get('payments', [])
                if payments_data:
                    prepared_payments = []
                    for payment in payments_data:
                        payment_copy = payment.copy()
                        payment_copy['order'] = order.id

                        amount = payment_copy.get('amount')
                        if amount is not None:
                            payment_copy['amount'] = Decimal(str(amount))

                        payment_copy['payment_method'] = payment.get('payment_method', 'cash')
                        payment_copy['reference_number'] = payment.get('reference_number')
                        payment_copy['payment_date'] = payment.get('payment_date', str(date.today()))

                        prepared_payments.append(payment_copy)

                    total_paid = OrderPaymentService.process_payments(order, prepared_payments)

                    if total_paid >= order.total_price:
                        order.status = 'paid'
                    elif total_paid > 0:
                        order.status = 'partially_paid'
                    order.save()

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"An unexpected error occurred: {str(e)}"}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
