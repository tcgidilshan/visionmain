from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta, datetime, date
from ..models import OrderPayment,ChannelPayment,OtherIncome,Expense,BankDeposit,SafeTransaction,SolderingPayment,DailyCashInHandRecord,Order
from decimal import Decimal
from django.utils.timezone import is_naive, make_aware, localtime

class DailyFinanceSummaryService:

    @staticmethod
    def _sum(queryset, field='amount'):
        return queryset.aggregate(total=Sum(field)).get('total') or Decimal("0.00")

    @staticmethod
    def _ensure_timezone_aware(dt):
        """Ensure datetime is timezone-aware"""
        if isinstance(dt, datetime):
            if is_naive(dt):
                return make_aware(dt)
            return dt
        return dt

    @staticmethod
    def _get_date_range(date_obj):
        """Get timezone-aware start and end of day for a date"""
        if isinstance(date_obj, datetime):
            # If it's already a datetime, convert to date first
            date_obj = date_obj.date()
        
        # Create timezone-aware datetime for start of day
        start_of_day = timezone.make_aware(datetime.combine(date_obj, datetime.min.time()))
        end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)
      
        
        return start_of_day, end_of_day

    @staticmethod
    def get_previous_day_balance(branch_id, date):
        try:
            return DailyCashInHandRecord.objects.get(branch_id=branch_id, date=date).cash_in_hand
        except DailyCashInHandRecord.DoesNotExist:
            return Decimal("0.00")

    @staticmethod
    def get_safe_balance(branch_id, date):
        start_of_day, end_of_day = DailyFinanceSummaryService._get_date_range(date)
        
        result = SafeTransaction.objects.filter(
            branch_id=branch_id,
            transaction_type="income",
            date__gte=start_of_day,
            date__lte=end_of_day
        ).aggregate(total_amount=Sum('amount'))

        return result["total_amount"] or Decimal("0.00")

    @staticmethod
    def get_summary(branch_id, date=None):
        if date is None:
            date = timezone.localdate()
        elif isinstance(date, datetime):
            date = date.date()

        # Calculate and store the cash_in_hand for today and yesterday
        DailyFinanceSummaryService.calculate_for_day(branch_id, date)

        # Fetch all records excluding today and yesterday
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        
        records = DailyCashInHandRecord.objects.filter(branch_id=branch_id).exclude(
            date__in=[today, yesterday]
        )

        # Convert to timezone-aware ISO string
        historical_data = []
        for record in records:
            dt = record.date
            if isinstance(dt, datetime):
                dt = DailyFinanceSummaryService._ensure_timezone_aware(dt)
                dt = localtime(dt).isoformat()
            else:
                # Assume it's a `date` object, convert to timezone-aware datetime
                dt = timezone.make_aware(datetime.combine(dt, datetime.min.time())).isoformat()

            historical_data.append({
                'date': dt,
                'cash_in_hand': record.cash_in_hand
            })

        # print(f"Historical data (excluding today and yesterday): {historical_data}")

        # Optionally: return full report including historical
        summary = DailyFinanceSummaryService.calculate_for_day(branch_id, date)
        summary['historical_data'] = historical_data  # Include in response
        return summary

    @staticmethod
    def calculate_for_day(branch_id, date):
        if isinstance(date, datetime):
            date = date.date()
            
        yesterday = date - timedelta(days=1)
        start_of_day, end_of_day = DailyFinanceSummaryService._get_date_range(date)
        start_of_yesterday, end_of_yesterday = DailyFinanceSummaryService._get_date_range(yesterday)

        # Get previous day's balance (if any)
        previous_balance = DailyFinanceSummaryService.get_previous_day_balance(branch_id, yesterday)
        yesterday_safe_income = DailyFinanceSummaryService.get_safe_balance(branch_id, yesterday)
        today_safe_balance = DailyFinanceSummaryService.get_safe_balance(branch_id, date)
        yesterday_safe_income = DailyFinanceSummaryService.get_safe_balance(branch_id, yesterday)
        today_safe_balance = DailyFinanceSummaryService.get_safe_balance(branch_id, date)

        # Yesterday calculations
        yesterday_order_payments = DailyFinanceSummaryService._sum(
            OrderPayment.all_objects.filter(
                order__branch_id=branch_id, 
                payment_date__gte=start_of_yesterday,
                payment_date__lte=end_of_yesterday,
                payment_method="cash",
                is_edited=False,
          
            )
        )
        yesterday_channel_payments = DailyFinanceSummaryService._sum(
            ChannelPayment.all_objects.filter(
                appointment__branch_id=branch_id, 
                payment_date__gte=start_of_yesterday,
                payment_date__lte=end_of_yesterday,
                payment_method="cash",
             
                is_edited=False
            )
        )
        yesterday_other_income = DailyFinanceSummaryService._sum(
            OtherIncome.objects.filter(
                branch_id=branch_id, 
                date__gte=start_of_yesterday,
                date__lte=end_of_yesterday
            )
        )
        yesterday_soldering_income = DailyFinanceSummaryService._sum(
            SolderingPayment.objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_yesterday,
                payment_date__lte=end_of_yesterday,
                payment_method="cash"
            )
        )
        yesterday_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(
                branch_id=branch_id, 
                created_at__gte=start_of_yesterday,
                created_at__lte=end_of_yesterday,
                paid_source="cash",
                is_refund=False
            )
        )

        # before_balance = (
        #     yesterday_order_payments +
        #     yesterday_channel_payments +
        #     yesterday_other_income +
        #     yesterday_soldering_income
        # ) - (yesterday_expenses + yesterday_safe_income)
        
        #get orderids softdeleted and refundeed also not soft deleted
      
        # Today calculations
        today_order_payments = DailyFinanceSummaryService._sum(
            OrderPayment.all_objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="cash",
                is_edited=False,
            )
        )
        data=  OrderPayment.all_objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="cash",
                is_edited=False,
            )

        today_channel_payments = DailyFinanceSummaryService._sum(
            ChannelPayment.all_objects.filter(
                appointment__branch_id=branch_id, 
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="cash",
                is_edited=False,
            )
        )
       
        today_other_income = DailyFinanceSummaryService._sum(
            OtherIncome.objects.filter(
                branch_id=branch_id, 
                date__gte=start_of_day,
                date__lte=end_of_day
            )
        )
        today_soldering_income = DailyFinanceSummaryService._sum(
            SolderingPayment.objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="cash"
            )
        )
        today_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(
                branch_id=branch_id, 
                created_at__gte=start_of_day,
                created_at__lte=end_of_day,
                paid_source="cash",
                # is_refund=False
            )
        )
        today_safe_expenses = DailyFinanceSummaryService._sum(
            Expense.objects.filter(
                branch_id=branch_id, 
                created_at__gte=start_of_day,
                created_at__lte=end_of_day,
                paid_source="safe",
                is_refund=False
            )
        )

        # Today balance calculation with safe balance included
        today_balance = (
            today_order_payments +
            today_channel_payments +
            today_other_income +
            today_soldering_income
        ) - (today_expenses + today_safe_balance)
      
        cash_in_hand = previous_balance + today_balance

        today_banking_qs = BankDeposit.objects.select_related('bank_account').filter(
            branch_id=branch_id,
            date__gte=start_of_day,
            date__lte=end_of_day
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

        # # ✅ Safe write to DB
        DailyCashInHandRecord.objects.update_or_create(
            branch_id=branch_id,
            date=date,
            defaults={
                'cash_in_hand': cash_in_hand,
                'before_balance': previous_balance,
                'today_balance': today_balance,
            }
        )
        #total online_transfer payment from orders
        today_order_payments_online_transfer = DailyFinanceSummaryService._sum(
            OrderPayment.all_objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="online_transfer",
                is_edited=False,
            )
        )
        #credit card payment from orders
        today_order_payments_credit_card = DailyFinanceSummaryService._sum(
            OrderPayment.all_objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="credit_card",
                is_edited=False,
            )
        )
        today_order_payments_cash = DailyFinanceSummaryService._sum(
            OrderPayment.all_objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="cash",
                is_edited=False,
            )
        )
        #total online_transfer payment from channel
        today_channel_payments_online_transfer = DailyFinanceSummaryService._sum(
            ChannelPayment.all_objects.filter(
                appointment__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="online_transfer",
                is_edited=False,
            )
        )
        #total credit card payment from channel
        today_channel_payments_credit_card = DailyFinanceSummaryService._sum(
            ChannelPayment.objects.filter(
                appointment__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="credit_card",
                is_edited=False,
            )
        )
        #total cash payment from channel
        today_channel_payments_cash = DailyFinanceSummaryService._sum(
            ChannelPayment.objects.filter(
                appointment__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="cash",
                is_edited=False,
            )
        )
        #total online_transfer payment from soldering
        today_soldering_payments_online_transfer = DailyFinanceSummaryService._sum(
            SolderingPayment.objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="online_transfer",
                # is_edited=False,
            )
        ) 
        #total credit card payment from soldering
        today_soldering_payments_credit_card = DailyFinanceSummaryService._sum(
            SolderingPayment.objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="credit_card",
            )
        )
        #total cash payment from soldering
        today_soldering_payments_cash = DailyFinanceSummaryService._sum(
            SolderingPayment.objects.filter(
                order__branch_id=branch_id,
                payment_date__gte=start_of_day,
                payment_date__lte=end_of_day,
                payment_method="cash",
            )
        )
        #grand total online payments from orders
        today_total_online_payments = today_order_payments_online_transfer + today_channel_payments_online_transfer + today_soldering_payments_online_transfer
        #grand total credit card payment from orders
        today_total_credit_card_payments = today_order_payments_credit_card + today_channel_payments_credit_card + today_soldering_payments_credit_card
        #grand total cash payment from orders
        today_total_cash_payments = today_order_payments_cash + today_channel_payments_cash + today_soldering_payments_cash
        
        return {
            "branch": branch_id,
            "date": str(date),
            "today_order_payments": today_order_payments_online_transfer+today_order_payments_credit_card+today_order_payments_cash,
            "today_channel_payments": today_channel_payments_online_transfer+today_channel_payments_credit_card+today_channel_payments_cash,
            "today_soldering_payments": today_soldering_payments_online_transfer+today_soldering_payments_credit_card+today_soldering_payments_cash,
            "today_other_income": today_other_income,
            "today_expenses": today_expenses + today_safe_expenses,
            "before_balance": previous_balance,
            "today_balance": today_balance,
            "cash_in_hand": cash_in_hand,
            "available_for_deposit": cash_in_hand,
            "today_banking_total": today_banking_total,
            "today_banking": today_banking_list,
            "today_total_online_payments":today_total_online_payments,
            "today_total_credit_card_payments":today_total_credit_card_payments,
            "today_total_cash_payments":today_total_cash_payments,
        }

