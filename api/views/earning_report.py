from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.db.models.functions import TruncYear, TruncMonth, TruncDate
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ..services.time_zone_convert_service import TimezoneConverterService
from ..models import Invoice, Appointment, OrderPayment, ChannelPayment, Expense, ExpenseReturn, SolderingInvoice, SolderingPayment, BankDeposit


class EarningReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get_period_data(self, period_start, period_end, branch_id_int):
        """Helper method to get earning data for a specific period"""
        # Counts - using timezone-aware datetime range
        invoices = Invoice.objects.filter(
            invoice_date__gte=period_start,
            invoice_date__lt=period_end,
            order__branch_id=branch_id_int,
            is_deleted=False
        )
        factory_order_count = invoices.filter(invoice_type='factory').count()
        normal_order_count = invoices.filter(invoice_type='normal').count()
        hearing_order_count = invoices.filter(invoice_type='hearing').count()

        # SolderingInvoice
        soldering_order_count = SolderingInvoice.objects.filter(
            invoice_date__gte=period_start.date(),
            invoice_date__lte=period_end.date(),
            order__branch_id=branch_id_int,
            is_deleted=False
        ).count()

        # Appointments
        channel_count = Appointment.objects.filter(
            created_at__gte=period_start,
            created_at__lt=period_end,
            branch_id=branch_id_int,
            is_deleted=False
        ).count()

        # Amounts - calculate total payments first, then subtract refunds
        factory_order_payment_total = OrderPayment.objects.filter(
            order__invoice__invoice_type='factory',
            order__invoice__invoice_date__gte=period_start,
            order__invoice__invoice_date__lt=period_end,
            order__branch_id=branch_id_int,
            order__invoice__is_deleted=False,
            payment_date__gte=period_start,
            payment_date__lt=period_end,
            is_deleted=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        factory_order_refund = Expense.objects.filter(
            order_refund__invoice__invoice_type='factory',
            order_refund__branch_id=branch_id_int,
            is_refund=True,
            order_refund__isnull=False,
            created_at__gte=period_start,
            created_at__lt=period_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        factory_order_amount = factory_order_payment_total - factory_order_refund

        normal_order_payment_total = OrderPayment.objects.filter(
            order__invoice__invoice_type='normal',
            order__invoice__invoice_date__gte=period_start,
            order__invoice__invoice_date__lt=period_end,
            order__branch_id=branch_id_int,
            order__invoice__is_deleted=False,
            payment_date__gte=period_start,
            payment_date__lt=period_end,
            is_deleted=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        normal_order_refund = Expense.objects.filter(
            order_refund__invoice__invoice_type='normal',
            order_refund__branch_id=branch_id_int,
            is_refund=True,
            order_refund__isnull=False,
            created_at__gte=period_start,
            created_at__lt=period_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        normal_order_amount = normal_order_payment_total - normal_order_refund

        hearing_order_payment_total = OrderPayment.objects.filter(
            order__invoice__invoice_type='hearing',
            order__invoice__invoice_date__gte=period_start,
            order__invoice__invoice_date__lt=period_end,
            order__branch_id=branch_id_int,
            order__invoice__is_deleted=False,
            payment_date__gte=period_start,
            payment_date__lt=period_end,
            is_deleted=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        hearing_order_refund = Expense.objects.filter(
            order_refund__invoice__invoice_type='hearing',
            order_refund__branch_id=branch_id_int,
            is_refund=True,
            order_refund__isnull=False,
            created_at__gte=period_start,
            created_at__lt=period_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        hearing_order_amount = hearing_order_payment_total - hearing_order_refund

        soldering_order_amount = SolderingPayment.objects.filter(
            order__branch_id=branch_id_int,
            payment_date__gte=period_start,
            payment_date__lt=period_end,
            is_deleted=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        channel_amount = ChannelPayment.objects.filter(
            appointment__branch_id=branch_id_int,
            appointment__created_at__gte=period_start,
            appointment__created_at__lt=period_end,
            appointment__is_deleted=False,
            payment_date__gte=period_start,
            payment_date__lt=period_end,
            is_deleted=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # Expense amount - exclude order refunds (they're already deducted from order amounts)
        expense_amount = Expense.objects.filter(
            branch_id=branch_id_int,
            created_at__gte=period_start,
            created_at__lt=period_end,
            order_refund__isnull=True  # Only get expenses that are NOT order refunds
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        expense_return_amount = ExpenseReturn.objects.filter(
            branch_id=branch_id_int,
            created_at__gte=period_start,
            created_at__lt=period_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # BankDeposit - using date field (DateField, not DateTimeField)
        bank_deposit_amount = BankDeposit.objects.filter(
            branch_id=branch_id_int,
            date__gte=period_start.date(),
            date__lte=period_end.date()
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        return {
            "factory_order_count": factory_order_count,
            "normal_order_count": normal_order_count,
            "hearing_order_count": hearing_order_count,
            "soldering_order_count": soldering_order_count,
            "channel_count": channel_count,
            "factory_order_amount": factory_order_amount,
            "normal_order_amount": normal_order_amount,
            "hearing_order_amount": hearing_order_amount,
            "soldering_order_amount": soldering_order_amount,
            "channel_amount": channel_amount,
            "expense_amount": expense_amount,
            "Expense_return_amount": expense_return_amount,
            "bank_deposit_amount": bank_deposit_amount
        }

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        report_type = request.query_params.get('type', 'daily')  # daily, monthly, yearly

        if not start_date or not end_date or not branch_id:
            return Response({
                "error": "start_date, end_date, and branch_id are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if report_type not in ['daily', 'monthly', 'yearly']:
            return Response({
                "error": "type must be one of: daily, monthly, yearly"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
            branch_id_int = int(branch_id)

            if report_type == 'daily':
                # Group by day
                results = []
                current_date = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
                
                while current_date < end_datetime:
                    # Calculate day boundaries
                    day_start = current_date
                    day_end = current_date + timedelta(days=1)
                    
                    # Adjust to actual range boundaries
                    if day_start < start_datetime:
                        day_start = start_datetime
                    if day_end > end_datetime:
                        day_end = end_datetime

                    period_data = self.get_period_data(day_start, day_end, branch_id_int)
                    period_data['date'] = current_date.strftime('%Y-%m-%d')
                    results.append(period_data)
                    
                    current_date = day_end

                # Calculate summary
                summary = {
                    "factory_order_count": sum(r['factory_order_count'] for r in results),
                    "normal_order_count": sum(r['normal_order_count'] for r in results),
                    "hearing_order_count": sum(r['hearing_order_count'] for r in results),
                    "soldering_order_count": sum(r['soldering_order_count'] for r in results),
                    "channel_count": sum(r['channel_count'] for r in results),
                    "factory_order_amount": sum(r['factory_order_amount'] for r in results),
                    "normal_order_amount": sum(r['normal_order_amount'] for r in results),
                    "hearing_order_amount": sum(r['hearing_order_amount'] for r in results),
                    "soldering_order_amount": sum(r['soldering_order_amount'] for r in results),
                    "channel_amount": sum(r['channel_amount'] for r in results),
                    "expense_amount": sum(r['expense_amount'] for r in results),
                    "Expense_return_amount": sum(r['Expense_return_amount'] for r in results),
                    "bank_deposit_amount": sum(r['bank_deposit_amount'] for r in results)
                }

                return Response({"data": results, "summary": summary})

            elif report_type == 'yearly':
                # Group by year
                results = []
                current_year = start_datetime.year
                end_year = end_datetime.year

                while current_year <= end_year:
                    year_start = start_datetime.replace(year=current_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    year_end = start_datetime.replace(year=current_year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    
                    # Adjust to actual range boundaries
                    if year_start < start_datetime:
                        year_start = start_datetime
                    if year_end > end_datetime:
                        year_end = end_datetime

                    period_data = self.get_period_data(year_start, year_end, branch_id_int)
                    period_data['date'] = str(current_year)
                    results.append(period_data)
                    
                    current_year += 1

                # Calculate summary
                summary = {
                    "factory_order_count": sum(r['factory_order_count'] for r in results),
                    "normal_order_count": sum(r['normal_order_count'] for r in results),
                    "hearing_order_count": sum(r['hearing_order_count'] for r in results),
                    "soldering_order_count": sum(r['soldering_order_count'] for r in results),
                    "channel_count": sum(r['channel_count'] for r in results),
                    "factory_order_amount": sum(r['factory_order_amount'] for r in results),
                    "normal_order_amount": sum(r['normal_order_amount'] for r in results),
                    "hearing_order_amount": sum(r['hearing_order_amount'] for r in results),
                    "soldering_order_amount": sum(r['soldering_order_amount'] for r in results),
                    "channel_amount": sum(r['channel_amount'] for r in results),
                    "expense_amount": sum(r['expense_amount'] for r in results),
                    "Expense_return_amount": sum(r['Expense_return_amount'] for r in results),
                    "bank_deposit_amount": sum(r['bank_deposit_amount'] for r in results)
                }

                return Response({"data": results, "summary": summary})

            elif report_type == 'monthly':
                # Group by month
                results = []
                current_date = start_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                while current_date < end_datetime:
                    # Calculate month boundaries
                    month_start = current_date
                    month_end = (current_date + relativedelta(months=1))
                    
                    # Adjust to actual range boundaries
                    if month_start < start_datetime:
                        month_start = start_datetime
                    if month_end > end_datetime:
                        month_end = end_datetime

                    period_data = self.get_period_data(month_start, month_end, branch_id_int)
                    period_data['date'] = current_date.strftime('%Y-%m')
                    results.append(period_data)
                    
                    current_date = month_end

                # Calculate summary
                summary = {
                    "factory_order_count": sum(r['factory_order_count'] for r in results),
                    "normal_order_count": sum(r['normal_order_count'] for r in results),
                    "hearing_order_count": sum(r['hearing_order_count'] for r in results),
                    "soldering_order_count": sum(r['soldering_order_count'] for r in results),
                    "channel_count": sum(r['channel_count'] for r in results),
                    "factory_order_amount": sum(r['factory_order_amount'] for r in results),
                    "normal_order_amount": sum(r['normal_order_amount'] for r in results),
                    "hearing_order_amount": sum(r['hearing_order_amount'] for r in results),
                    "soldering_order_amount": sum(r['soldering_order_amount'] for r in results),
                    "channel_amount": sum(r['channel_amount'] for r in results),
                    "expense_amount": sum(r['expense_amount'] for r in results),
                    "Expense_return_amount": sum(r['Expense_return_amount'] for r in results),
                    "bank_deposit_amount": sum(r['bank_deposit_amount'] for r in results)
                }

                return Response({"data": results, "summary": summary})

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)