from rest_framework.exceptions import ValidationError
from ..models import SolderingPayment
from decimal import Decimal
from django.db import models

class SolderingPaymentService:
    @staticmethod
    def process_solder_payments(order, payments_data):

        total_paid = Decimal('0.00')
        payment_instances = []
        final_payment_flagged = False

        for payment in payments_data:
            amount = Decimal(str(payment.get('amount', 0)))

            # 1. Block all negative payments. Block zero unless order price is zero.
            if amount < 0 or (amount == 0 and order.price != 0):
                raise ValidationError("Zero-amount payment is only allowed if order price is zero.")

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
                is_partial=False,  
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

    @staticmethod
    def add_repayment(order, amount, payment_method, is_final_payment=False):
        """
        Add a repayment for a soldering order with validation.
        This method now uses DRF's ValidationError to ensure API-friendly errors.
        """
        # Block repayments to deleted orders
        if order.is_deleted:
            raise ValidationError("Cannot add repayment to a deleted order.")

        # Sum existing payments (exclude soft-deleted)
        total_paid = SolderingPayment.objects.filter(
            order=order, is_deleted=False
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        remaining = order.price - total_paid

        # Block invalid or overpayment amounts
        if amount <= 0:
            raise ValidationError("Repayment amount must be positive.")
        if amount > remaining:
            raise ValidationError("Repayment exceeds remaining order balance.")

        # Allow only one final payment
        if is_final_payment and SolderingPayment.objects.filter(
            order=order, is_final_payment=True, is_deleted=False
        ).exists():
            raise ValidationError("A final payment has already been made for this order.")

        # Create and return the payment instance
        payment = SolderingPayment.objects.create(
            order=order,
            amount=amount,
            payment_method=payment_method,
            transaction_status=SolderingPayment.TransactionStatus.COMPLETED,
            is_final_payment=is_final_payment,
            is_partial=(amount != remaining)
        )
        return payment

        