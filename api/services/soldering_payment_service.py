from django.core.exceptions import ValidationError
from ..models import SolderingPayment
from decimal import Decimal

class SolderingPaymentService:
    @staticmethod
    def process_solder_payments(order, payments_data):
        if not payments_data:
            raise ValidationError("At least one payment record is required.")

        total_paid = Decimal('0.00')
        payment_instances = []
        final_payment_flagged = False

        for payment in payments_data:
            amount = Decimal(str(payment.get('amount', 0)))
            if amount <= 0:
                raise ValidationError("Each payment amount must be greater than zero.")

            method = payment.get('payment_method')
            is_final = payment.get('is_final_payment', False)

            if is_final:
                if final_payment_flagged:
                    raise ValidationError("Only one payment can be marked as final.")
                final_payment_flagged = True

            total_paid += amount

            payment_instance = SolderingPayment.objects.create(
                order=order,
                amount=amount,
                payment_method=method,
                transaction_status=SolderingPayment.TransactionStatus.COMPLETED,
                is_final_payment=is_final,
                is_partial=False  # We'll adjust this after total is known
            )

            payment_instances.append(payment_instance)

        if total_paid > order.price:
            raise ValidationError("Total payments exceed the order price.")

        # Determine partial flags
        is_full_payment = total_paid == order.price
        for payment in payment_instances:
            payment.is_partial = not is_full_payment
            payment.save()

        return payment_instances
