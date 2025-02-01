from ..models import OrderPayment
from ..serializers import OrderPaymentSerializer

class OrderPaymentService:
    """
    Handles processing of order payments.
    """
    @staticmethod
    def process_payments(order, payments_data):
        total_payment = 0
        for payment_data in payments_data:
            payment_data['order'] = order.id

            # Determine if this payment is partial
            payment_data['is_partial'] = total_payment + payment_data['amount'] < order.total_price

            # Validate and save each payment
            order_payment_serializer = OrderPaymentSerializer(data=payment_data)
            order_payment_serializer.is_valid(raise_exception=True)
            payment_instance = order_payment_serializer.save()

            # Track total payment
            total_payment += payment_data['amount']

            # Check if this is the final payment
            payment_instance.is_final_payment = total_payment == order.total_price
            payment_instance.save()

        return total_payment
