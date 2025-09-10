from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from ..models import SolderingOrder, SolderingPayment
from django.db import models
class SolderingOrderService:
    @staticmethod
    def create_order(*, patient, branch, price, note="", progress_status=None, status=None):
        # Convert price to Decimal if it's not already
        try:
            price = Decimal(str(price))
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid price format: {str(e)}")
        
        if price < 0:
            raise ValidationError("Price must be greater than or equal to 0.")

        order = SolderingOrder.objects.create(
            patient=patient,
            branch=branch,
            price=price,
            note=note,
            status=status or SolderingOrder.Status.PENDING,
            order_date=timezone.now(),
            progress_status=progress_status or SolderingOrder.ProgressStatus.RECEIVED_FROM_CUSTOMER,
        )

        return order


class SolderingPaymentService:
    # ...other methods...

    @staticmethod
    def add_repayment(order, amount, payment_method, is_final_payment=False):
        """
        Adds a repayment to a soldering order, with full business validation.
        Ensures medical finance auditability and compliance.
        """
        #TODO security: Block repayments to deleted/cancelled orders.
        if order.is_deleted:
            raise ValidationError("Cannot add repayment to a deleted order.")

        # Calculate total paid so far (only non-deleted payments)
        total_paid = SolderingPayment.objects.filter(
            order=order, is_deleted=False
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        remaining = order.price - total_paid  # Remaining balance

        # Block zero or negative payments (critical for audit integrity)
        if amount <= 0:
            raise ValidationError("Repayment amount must be positive.")

        # Prevent over-payment, which is a compliance and UX error
        if amount > remaining:
            raise ValidationError("Repayment exceeds remaining order balance.")

        # Block multiple final payments for same order (medical finance best practice)
        if is_final_payment:
            if SolderingPayment.objects.filter(order=order, is_final_payment=True, is_deleted=False).exists():
                raise ValidationError("A final payment has already been made for this order.")

        # Create the repayment (all business logic passed)
        payment = SolderingPayment.objects.create(
            order=order,
            amount=amount,
            payment_method=payment_method,
            transaction_status=SolderingPayment.TransactionStatus.COMPLETED,
            is_final_payment=is_final_payment,
            is_partial=(amount != remaining),  # Mark as partial if not settling balance
        )
        # Payment is now auditable (who, when, how much)
        return payment
