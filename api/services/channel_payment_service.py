from ..models import ChannelPayment,Appointment
from decimal import Decimal


class ChannelPaymentService:
    @staticmethod
    def create_repayment(appointment, amount, method):
        # Prevent if already finalized
        if appointment.payments.filter(is_final=True).exists():
            raise ValueError("Final payment has already been made.")

        if amount is None:
            # Auto-calculate remaining amount
            amount = appointment.get_remaining_amount()

        # Re-check after calculation
        if amount <= 0:
            raise ValueError("No remaining balance to pay.")

        # Determine if this is the final payment
        total_paid = appointment.get_total_paid() + Decimal(str(amount))
        is_final = total_paid >= appointment.amount

        # Save payment
        payment = ChannelPayment.objects.create(
            appointment=appointment,
            amount=amount,
            payment_method=method,
            is_final=is_final
        )

        if is_final:
            appointment.status = Appointment.StatusChoices.COMPLETED
            appointment.save()

        return payment
