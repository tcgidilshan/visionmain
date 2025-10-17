from ..models import ChannelPayment,Appointment
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Appointment
from ..models import Expense
from ..serializers import ExpenseSerializer
from django.db.models import Sum
from ..models import PaymentMethodBanks
class ChannelPaymentService:
    @staticmethod
    def create_repayment(appointment, amount, method, payment_method_bank=None, payment_date=None):
        # Prevent if already finalized
        if appointment.payments.filter(is_final=True).exists():
            raise ValueError("Final payment has already been made.")
        
        # Use current date/time if payment_date is not provided
        if payment_date is None:
            payment_date = timezone.now()

        if amount is None:
            # Auto-calculate remaining amount
            amount = appointment.get_remaining_amount()

        # Re-check after calculation
        if amount <= 0:
            raise ValueError("No remaining balance to pay.")

        # Determine if this is the final payment
        total_paid = appointment.get_total_paid() + Decimal(str(amount))
        is_final = total_paid >= appointment.amount

        # Convert payment_method_bank ID to instance if needed
        bank_instance = None
        if payment_method_bank:
            try:
                bank_instance = PaymentMethodBanks.objects.get(id=payment_method_bank)
            except PaymentMethodBanks.DoesNotExist:
                bank_instance = None

        print("Bank instance:", bank_instance)
        print("Raw payment_method_bank value:", payment_method_bank)

        # Save payment
        payment = ChannelPayment.objects.create(
            appointment=appointment,
            amount=amount,
            payment_method=method,
            is_final=is_final,
            payment_method_bank=bank_instance,
            payment_date=payment_date
        )

        if is_final:
            appointment.status = Appointment.StatusChoices.COMPLETED
            appointment.save()

        return payment
    
    @staticmethod
    @transaction.atomic
    def refund_channel(appointment_id, expense_data):
        try:
            appointment = Appointment.all_objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ValidationError("Appointment not found.")

        if appointment.is_refund:
            raise ValidationError("This appointment has already been refunded.")

        # Step 1: Mark as refunded
        appointment.is_refund = True
        appointment.refunded_at = timezone.now()
        appointment.refund_note = f"Refunded via expense #{timezone.now().isoformat()}"
        appointment.save()
        #get total amount of payments
        total_amount = ChannelPayment.objects.filter(appointment_id=appointment.id, is_deleted=False).aggregate(total_amount=Sum('amount'))['total_amount']
        ChannelPayment.objects.filter(appointment_id=appointment.id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
        # Step 2: Enrich expense data
        expense_data['amount'] = str(total_amount)
        expense_data['note'] = f"Refund invoice - {appointment.invoice_number}"
        expense_data['paid_source'] = "cash"
        expense_data['is_refund'] = True
        expense_data['paid_from_safe'] =False

        # Step 3: Create expense
        serializer = ExpenseSerializer(data=expense_data)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()

        return {
            "message": "Refund processed successfully.",
            "appointment_id": appointment.id,
            "refund_expense_id": expense.id
        }

