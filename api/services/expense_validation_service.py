from django.db.models import Sum
from django.core.exceptions import ValidationError
from datetime import date
from ..models import Expense, OrderPayment, ChannelPayment,SolderingPayment
from ..services.finance_summary_service import DailyFinanceSummaryService

class ExpenseValidationService:

    @staticmethod
    def validate_expense_limit(branch_id, amount):
        summary = DailyFinanceSummaryService.get_summary(branch_id)  # Pass the branch_id
        # print(summary['cash_in_hand'])  
        today = date.today()

        # # 🔹 Sum of Order Payments
        # order_total = OrderPayment.objects.filter(
        #     order__branch_id=branch_id,
        #     payment_date__date=today,
        #     payment_method="cash"
        # ).aggregate(total=Sum('amount'))['total'] or 0

        # # 🔹 Sum of Channel Payments
        # channel_total = ChannelPayment.objects.filter(
        #     appointment__branch_id=branch_id,
        #     payment_date__date=today,
        #     payment_method="cash"
        # ).aggregate(total=Sum('amount'))['total'] or 0

        # soldering_total = SolderingPayment.objects.filter(
        #     order__branch_id=branch_id,
        #     payment_date__date=today,
        #     payment_method="cash" 
        #     ).aggregate(total=Sum('amount'))['total'] or 0

        total_available = summary['cash_in_hand']
        # 🔹 Sum of today's expenses
        total_expenses = Expense.objects.filter(
            branch_id=branch_id,
            created_at__date=today,
        ).aggregate(total=Sum('amount'))['total'] or 0

        if (total_expenses + amount) > total_available:
            raise ValidationError(
                "🚫 Expense exceeds today's available income. "
                f"Available: {total_available}, Attempted: {total_expenses + amount}"
            )

    @staticmethod
    def get_total_payments_for_date(branch_id, date):
        """
        Returns the total of all payment methods for a given date and branch.
        Includes OrderPayment and ChannelPayment models.
        """
        order_total = OrderPayment.objects.filter(
            order__branch_id=branch_id,
            payment_date__date=date
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        channel_total = ChannelPayment.objects.filter(
            appointment__branch_id=branch_id,
            payment_date__date=date
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        return order_total + channel_total

    @staticmethod
    def validate_expense_update(expense_instance, new_amount, branch_id, date):
        total_paid = ExpenseValidationService.get_total_payments_for_date(branch_id, date)

        total_expenses = Expense.objects.filter(
            branch_id=branch_id,
            created_at__date=date
        ).exclude(id=expense_instance.id).aggregate(
            Sum("amount")
        )["amount__sum"] or 0

        new_total = total_expenses + new_amount
        if new_total > total_paid:
            raise ValueError("Updated expense exceeds the available income for the day.")
