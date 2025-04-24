from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from ..models import OrderPayment,ChannelPayment,OtherIncome,Expense,BankDeposit 

class DailyFinanceSummaryService:

    @staticmethod
    def get_summary(branch_id, date=None):
        if date is None:
            date = timezone.localdate()

        yesterday = date - timedelta(days=1)

        def _sum(queryset, field='amount'):
            return queryset.aggregate(total=Sum(field)).get('total') or 0

        # 🔹 YESTERDAY
        yesterday_order_payments = _sum(OrderPayment.objects.filter(
            order__branch_id=branch_id,
            payment_date__date=yesterday,
            transaction_status='success'
        ))

        yesterday_channel_payments = _sum(ChannelPayment.objects.filter(
            appointment__branch_id=branch_id,
            payment_date__date=yesterday
        ))

        yesterday_other_income = _sum(OtherIncome.objects.filter(
            branch_id=branch_id,
            date=yesterday
        ))

        yesterday_expenses = _sum(Expense.objects.filter(
            branch_id=branch_id,
            created_at__date=yesterday
        ))

        yesterday_banking = _sum(BankDeposit.objects.filter(
            branch_id=branch_id,
            date=yesterday
        ))

        before_balance = (
            yesterday_order_payments +
            yesterday_channel_payments +
            yesterday_other_income
        ) - (
            yesterday_expenses +
            yesterday_banking
        )

        # 🔹 TODAY
        today_order_payments = _sum(OrderPayment.objects.filter(
            order__branch_id=branch_id,
            payment_date__date=date,
            transaction_status='success'
        ))

        today_channel_payments = _sum(ChannelPayment.objects.filter(
            appointment__branch_id=branch_id,
            payment_date__date=date
        ))

        today_other_income = _sum(OtherIncome.objects.filter(
            branch_id=branch_id,
            date=date
        ))

        today_expenses = _sum(Expense.objects.filter(
            branch_id=branch_id,
            created_at__date=date
        ))

        today_banking_qs = BankDeposit.objects.select_related('bank_account').filter(
            branch_id=branch_id,
            date=date
        )

        today_banking_total = _sum(today_banking_qs)

        today_banking_list = [
            {
                "bank_name": deposit.bank_account.bank_name,
                "account_number": deposit.bank_account.account_number,
                "amount": deposit.amount,
                "is_confirmed": deposit.is_confirmed
            }
            for deposit in today_banking_qs
        ]

        # 🔹 CALCULATIONS
        today_income = today_order_payments + today_channel_payments + today_other_income
        today_balance = today_income - (today_expenses + today_banking_total)
        cash_in_hold = before_balance + today_balance

        return {
            "branch": branch_id,
            "date": str(date),

            "before_balance": before_balance,
            "today_order_payments": today_order_payments,
            "today_channel_payments": today_channel_payments,
            "today_other_income": today_other_income,

            "today_expenses": today_expenses,
            "today_banking": today_banking_list,

            "today_balance": today_balance,
            "cash_in_hold": cash_in_hold,
            "available_for_deposit": cash_in_hold  # Matches logic
        }
