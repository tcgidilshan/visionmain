from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from datetime import date
from ..models import OrderPayment,ChannelPayment,OtherIncome,Expense,BankDeposit,SafeTransaction

class DailyFinanceSummaryService:
    @staticmethod
    def _sum(queryset, field='amount'):
        return queryset.aggregate(total=Sum(field)).get('total') or 0

    @staticmethod
    def get_summary(branch_id, date=None):
        if date is None:
            date = date.today()

        yesterday = date - timedelta(days=1)

        # ========= YESTERDAY (General)
        yesterday_order_payments = DailyFinanceSummaryService._sum(OrderPayment.objects.filter(
            order__branch_id=branch_id,
            payment_date__date=yesterday,
            transaction_status='success'
        ))

        yesterday_channel_payments = DailyFinanceSummaryService._sum(ChannelPayment.objects.filter(
            appointment__branch_id=branch_id,
            payment_date__date=yesterday
        ))

        yesterday_other_income = DailyFinanceSummaryService._sum(OtherIncome.objects.filter(
            branch_id=branch_id,
            date=yesterday
        ))

        yesterday_expenses = DailyFinanceSummaryService._sum(Expense.objects.filter(
            branch_id=branch_id,
            created_at__date=yesterday
        ))

        yesterday_banking = DailyFinanceSummaryService._sum(BankDeposit.objects.filter(
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

        # ========= TODAY (General)
        today_order_payments = DailyFinanceSummaryService._sum(OrderPayment.objects.filter(
            order__branch_id=branch_id,
            payment_date__date=date,
            transaction_status='success'
        ))

        today_channel_payments = DailyFinanceSummaryService._sum(ChannelPayment.objects.filter(
            appointment__branch_id=branch_id,
            payment_date__date=date
        ))

        today_other_income = DailyFinanceSummaryService._sum(OtherIncome.objects.filter(
            branch_id=branch_id,
            date=date
        ))

        today_expenses = DailyFinanceSummaryService._sum(Expense.objects.filter(
            branch_id=branch_id,
            created_at__date=date
        ))

        today_banking_qs = BankDeposit.objects.select_related('bank_account').filter(
            branch_id=branch_id,
            date=date
        )
        today_banking_total = DailyFinanceSummaryService._sum(today_banking_qs)

        today_banking_list = [
            {
                "bank_name": deposit.bank_account.bank_name,
                "account_number": deposit.bank_account.account_number,
                "amount": deposit.amount,
                "is_confirmed": deposit.is_confirmed,
            }
            for deposit in today_banking_qs
        ]

        today_income = today_order_payments + today_channel_payments + today_other_income
        today_balance = today_income - (today_expenses + today_banking_total)
        cash_in_hold = before_balance + today_balance

        # ========= SAFE LOCKER LOGIC
        # Yesterday
        yesterday_safe_income = DailyFinanceSummaryService._sum(SafeTransaction.objects.filter(
            branch_id=branch_id,
            date=yesterday,
            transaction_type='income'
        ))
        yesterday_safe_expense = DailyFinanceSummaryService._sum(SafeTransaction.objects.filter(
            branch_id=branch_id,
            date=yesterday,
            transaction_type='expense'
        ))
        yesterday_safe_deposit = DailyFinanceSummaryService._sum(SafeTransaction.objects.filter(
            branch_id=branch_id,
            date=yesterday,
            transaction_type='deposit'
        ))

        safe_before_balance = yesterday_safe_income - (yesterday_safe_expense + yesterday_safe_deposit)

        # Today
        today_safe_income = DailyFinanceSummaryService._sum(SafeTransaction.objects.filter(
            branch_id=branch_id,
            date=date,
            transaction_type='income'
        ))
        today_safe_expense = DailyFinanceSummaryService._sum(SafeTransaction.objects.filter(
            branch_id=branch_id,
            date=date,
            transaction_type='expense'
        ))
        today_safe_deposit = DailyFinanceSummaryService._sum(SafeTransaction.objects.filter(
            branch_id=branch_id,
            date=date,
            transaction_type='deposit'
        ))

        safe_today_balance = today_safe_income - (today_safe_expense + today_safe_deposit)
        safe_cash_in_hold = safe_before_balance + safe_today_balance

        # ========= Final Summary
        return {
            "branch": branch_id,
            "date": str(date),

            # -- General --
            "before_balance": before_balance,
            "today_order_payments": today_order_payments,
            "today_channel_payments": today_channel_payments,
            "today_other_income": today_other_income,
            "today_expenses": today_expenses,
            "today_banking": today_banking_list,
            "today_balance": today_balance,
            "cash_in_hold": cash_in_hold,
            "available_for_deposit": cash_in_hold,

            # -- Safe Locker --
            "safe_before_balance": safe_before_balance,
            "safe_income": today_safe_income,
            "safe_expense": today_safe_expense,
            "safe_deposit": today_safe_deposit,
            "safe_today_balance": safe_today_balance,
            "safe_cash_in_hold": safe_cash_in_hold,
        }