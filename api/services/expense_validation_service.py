from django.db.models import Sum
from django.core.exceptions import ValidationError
from datetime import date
from ..models import Expense, OrderPayment, ChannelPayment  # import both

class ExpenseValidationService:
    @staticmethod
    def validate_expense_limit(branch_id, amount):
        today = date.today()

        # 🔹 Sum of Order Payments
        order_total = OrderPayment.objects.filter(
            order__branch_id=branch_id,
            payment_date__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0

        # 🔹 Sum of Channel Payments
        channel_total = ChannelPayment.objects.filter(
            appointment__branch_id=branch_id,
            payment_date__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_payments = order_total + channel_total

        # 🔹 Sum of today's expenses
        total_expenses = Expense.objects.filter(
            branch_id=branch_id,
            created_at__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0

        if (total_expenses + amount) > total_payments:
            raise ValidationError("🚫 Expense exceeds today's available income (orders + channels).")
