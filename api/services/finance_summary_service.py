from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta, datetime, date
from ..models import OrderPayment,ChannelPayment,OtherIncome,Expense,BankDeposit,SafeTransaction,SolderingPayment,DailyCashInHandRecord
from decimal import Decimal
from django.utils.timezone import is_naive, make_aware, localtime

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
    def get_safe_balance(branch_id, date):
        result = SafeTransaction.objects.filter(
            branch_id=branch_id,
            transaction_type="income",
            date=date
        ).aggregate(total_amount=Sum('amount'))

        return result["total_amount"] or Decimal("0.00")  # Default to 0 if no safe balance is set

    @staticmethod
    def get_summary(branch_id, date=None):
        if date is None:
            date = timezone.localdate()

        # Calculate and store the cash_in_hand for today and yesterday
        DailyFinanceSummaryService.calculate_for_day(branch_id, date)

        # Fetch all records excluding today and yesterday
        records = DailyCashInHandRecord.objects.filter(branch_id=branch_id).exclude(
            date__in=[timezone.localdate(), timezone.localdate() - timedelta(days=1)]
        )

        # Convert to timezone-aware ISO string
        historical_data = []
        for record in records:
            dt = record.date
            if isinstance(dt, datetime):
                if is_naive(dt):
                    dt = make_aware(dt)
                dt = localtime(dt).isoformat()
            else:
                # Assume it's a `date` object (safe), just convert to ISO string
                dt = dt.isoformat()

            historical_data.append({
                'date': dt,
                'cash_in_hand': record.cash_in_hand
            })

        print(f"Historical data (excluding today and yesterday): {historical_data}")

        # Optionally: return full report including historical
        summary = DailyFinanceSummaryService.calculate_for_day(branch_id, date)
        summary['historical_data'] = historical_data  # Include in response
        return summary


    @staticmethod
    def calculate_for_day(branch_id, date):
        from django.utils.timezone import is_aware

        # Ensure date is naive (MySQL-safe)
        if isinstance(date, datetime) and is_aware(date):
            date = date.replace(tzinfo=None)

        yesterday = date - timedelta(days=1)

        # Ensure yesterday is also naive
        if isinstance(yesterday, datetime) and is_aware(yesterday):
            yesterday = yesterday.replace(tzinfo=None)

        # Get previous day's balance
        previous_balance = DailyFinanceSummaryService.get_previous_day_balance(branch_id, yesterday)
        yesterday_safe_income = DailyFinanceSummaryService.get_safe_balance(branch_id, yesterday)
        today_safe_balance = DailyFinanceSummaryService.get_safe_balance(branch_id, date)

        # Yesterday calculations
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
            SolderingPayment.objects.filter(order__branch_id=branch_id, payment_date__date=yesterday, payment_method="cash")
        )
        yesterday_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(branch_id=branch_id, created_at__date=yesterday, paid_source="cash")
        )

        before_balance = (
            yesterday_order_payments +
            yesterday_channel_payments +
            yesterday_other_income +
            yesterday_soldering_income
        ) - (yesterday_expenses + yesterday_safe_income)

        # Today calculations
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
            SolderingPayment.objects.filter(order__branch_id=branch_id, payment_date__date=date, payment_method="cash")
        )
        today_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(branch_id=branch_id, created_at__date=date, paid_source="cash")
        )
        today_safe_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(branch_id=branch_id, created_at__date=date, paid_source="safe")
        )

        today_balance = (
            today_order_payments +
            today_channel_payments +
            today_other_income +
            today_soldering_income
        ) - (today_expenses + today_safe_balance)

        cash_in_hand = previous_balance + today_balance

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

        # ✅ Safe write to DB
        DailyCashInHandRecord.objects.update_or_create(
            branch_id=branch_id,
            date=date,
            defaults={
                'cash_in_hand': cash_in_hand,
                'before_balance': previous_balance,
                'today_balance': today_balance,
            }
        )

        return {
            "branch": branch_id,
            "date": str(date),
            "today_order_payments": today_order_payments,
            "today_channel_payments": today_channel_payments,
            "today_other_income": today_other_income,
            "today_expenses": today_expenses + today_safe_expenses,
            "before_balance": previous_balance,
            "today_balance": today_balance,
            "cash_in_hand": cash_in_hand,
            "available_for_deposit": cash_in_hand,
            "today_banking_total": today_banking_total,
            "today_banking": today_banking_list,
        }

