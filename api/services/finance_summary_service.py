from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from datetime import date
from ..models import OrderPayment,ChannelPayment,OtherIncome,Expense,BankDeposit,SafeTransaction,SolderingPayment,DailyCashInHandRecord
from decimal import Decimal

class DailyFinanceSummaryService:

    @staticmethod
    def _sum(queryset, field='amount'):
        return queryset.aggregate(total=Sum(field)).get('total') or Decimal("0.00")

    @staticmethod
    def get_previous_day_balance(branch_id, date):
        try:
            return DailyCashInHandRecord.objects.get(branch_id=branch_id, date=date).cash_in_hand
        except DailyCashInHandRecord.DoesNotExist:
            return Decimal("0.00")

    @staticmethod
    def get_summary(branch_id, date=None):
        if date is None:
            date = timezone.localdate()

        # Calculate and store the cash_in_hand for today and yesterday, but only save if needed
        DailyFinanceSummaryService.calculate_for_day(branch_id, date)

        # Fetch all records excluding today and yesterday
        records = DailyCashInHandRecord.objects.filter(branch_id=branch_id).exclude(
            date__in=[timezone.localdate(), timezone.localdate() - timedelta(days=1)]
        )

        # Return historical data (excluding today and yesterday)
        historical_data = [{'date': record.date, 'cash_in_hand': record.cash_in_hand} for record in records]
        print(f"Historical data (excluding today and yesterday): {historical_data}")

        # Return full summary for today (including today and yesterday calculations)
        return DailyFinanceSummaryService.calculate_for_day(branch_id, date)

    @staticmethod
    def calculate_for_day(branch_id, date):
        yesterday = date - timedelta(days=1)

        # Get previous day's balance (if any)
        previous_balance = DailyFinanceSummaryService.get_previous_day_balance(branch_id, yesterday)

        # ========== YESTERDAY
        yesterday_order_payments = DailyFinanceSummaryService._sum(
            OrderPayment.objects.filter(order__branch_id=branch_id, payment_date__date=yesterday, payment_method="cash")
        )
        yesterday_channel_payments = DailyFinanceSummaryService._sum(
            ChannelPayment.objects.filter(appointment__branch_id=branch_id, payment_date__date=yesterday, payment_method="cash")
        )
        yesterday_other_income = DailyFinanceSummaryService._sum(
            OtherIncome.objects.filter(branch_id=branch_id, date=yesterday)
        )
        yesterday_soldering_income = DailyFinanceSummaryService._sum(
            SolderingPayment.objects.filter(
                order__branch_id=branch_id,
                payment_date__date=yesterday,
                payment_method="cash"
            )
        )
        yesterday_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(branch_id=branch_id, created_at__date=yesterday, paid_source="cash")
        )

        before_balance = (
            yesterday_order_payments +
            yesterday_channel_payments +
            yesterday_other_income +
            yesterday_soldering_income
        ) - yesterday_expenses

        # ========== TODAY
        today_order_payments = DailyFinanceSummaryService._sum(
            OrderPayment.objects.filter(order__branch_id=branch_id, payment_date__date=date, payment_method="cash")
        )
        today_channel_payments = DailyFinanceSummaryService._sum(
            ChannelPayment.objects.filter(appointment__branch_id=branch_id, payment_date__date=date, payment_method="cash")
        )
        today_other_income = DailyFinanceSummaryService._sum(
            OtherIncome.objects.filter(branch_id=branch_id, date=date)
        )
        today_soldering_income = DailyFinanceSummaryService._sum(
            SolderingPayment.objects.filter(
                order__branch_id=branch_id,
                payment_date__date=date,
                payment_method="cash"
            )
        )
        today_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(branch_id=branch_id, created_at__date=date, paid_source="cash")
        )

        today_balance = (
            today_order_payments +
            today_channel_payments +
            today_other_income +
            today_soldering_income
        ) - today_expenses

        cash_in_hand = previous_balance + before_balance + today_balance

        # Fetch banking details for today
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

        # Update or create a record for the current date
        DailyCashInHandRecord.objects.update_or_create(
            branch_id=branch_id,
            date=date,
            defaults={
                'cash_in_hand': cash_in_hand,
                'before_balance': before_balance,
                'today_balance': today_balance,
            }
        )

        return {
            "branch": branch_id,
            "date": str(date),

            # Income Sources
            "today_order_payments": today_order_payments,
            "today_channel_payments": today_channel_payments,
            "today_other_income": today_other_income,

            # Expenses
            "today_expenses": today_expenses,

            # Summary
            "before_balance": before_balance,
            "today_balance": today_balance,
            "cash_in_hand": cash_in_hand,
            "available_for_deposit": cash_in_hand,

            # Bank
            "today_banking_total": today_banking_total,
            "today_banking": today_banking_list,
        }