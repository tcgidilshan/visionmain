from ..models import OrderPayment,Order
from ..serializers import OrderPaymentSerializer
from rest_framework.exceptions import ValidationError

class OrderPaymentService:
    """
    Handles processing of order payments.
    """
    @staticmethod
    def process_payments(order, payments_data):
        if order.is_deleted:
            raise ValidationError("Cannot process payments for a deleted order.")
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
    
    @staticmethod
    def update_process_payments(order, payments_data):
        """
        Updates existing payments, creates new ones if needed, and removes old ones.
        """
        existing_payments = {payment.id: payment for payment in order.orderpayment_set.all()}
        new_payment_ids = set()
        total_payment = 0

        for payment_data in payments_data:
            payment_id = payment_data.get("id")  # Check if payment exists

            if payment_id and payment_id in existing_payments:
                # ✅ Update existing payment
                existing_payment = existing_payments.pop(payment_id)
                existing_payment.amount = payment_data.get("amount", existing_payment.amount)
                existing_payment.payment_method = payment_data.get("payment_method", existing_payment.payment_method)
                existing_payment.transaction_status = payment_data.get("transaction_status", existing_payment.transaction_status)
                existing_payment.is_partial = total_payment + existing_payment.amount < order.total_price
                existing_payment.save()
                new_payment_ids.add(payment_id)
                total_payment += existing_payment.amount

            else:
                # ✅ Create a new payment
                payment_data['order'] = order.id
                payment_data['is_partial'] = total_payment + payment_data['amount'] < order.total_price

                order_payment_serializer = OrderPaymentSerializer(data=payment_data)
                order_payment_serializer.is_valid(raise_exception=True)
                payment_instance = order_payment_serializer.save()

                new_payment_ids.add(payment_instance.id)
                total_payment += payment_data['amount']

        # ✅ Remove payments that were not in the update request
        for old_payment in existing_payments.values():
            old_payment.delete()

        # ✅ Ensure total payments do not exceed the order total
        if total_payment > order.total_price:
            raise ValueError("Total payments exceed the order total price.")

        return total_payment
    
    @staticmethod
    def get_payments(order_id=None, invoice_id=None):
        """
        Fetch payments for a given order ID or invoice ID.
        """
        try:
            # ✅ Fetch order using order_id or invoice_id
            if order_id:
                order = Order.objects.get(id=order_id)
            elif invoice_id:
                order = Order.objects.get(invoice_id=invoice_id)
            else:
                return {"error": "Order ID or Invoice ID is required."}

            # ✅ Get payments related to the order
            payments = order.orderpayment_set.all()

            # ✅ Serialize payment data
            payment_serializer = OrderPaymentSerializer(payments, many=True)

            return {
                "message": "Payments fetched successfully.",
                "payments": payment_serializer.data
            }

        except Order.DoesNotExist:
            return {"error": "Order not found."}
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}

