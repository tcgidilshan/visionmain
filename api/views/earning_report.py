from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from ..services.time_zone_convert_service import TimezoneConverterService
from ..models import Invoice, Appointment, OrderPayment, ChannelPayment, Expense, ExpenseReturn, SolderingInvoice, SolderingPayment


class EarningReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')

        if not start_date or not end_date or not branch_id:
            return Response({
                "error": "start_date, end_date, and branch_id are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
            branch_id_int = int(branch_id)

            # Counts - using timezone-aware datetime range for Invoice.invoice_date (DateTimeField)
            invoices = Invoice.objects.filter(
                invoice_date__gte=start_datetime,
                invoice_date__lt=end_datetime,
                order__branch_id=branch_id_int,
                is_deleted=False
            )
            factory_order_count = invoices.filter(invoice_type='factory').count()
            normal_order_count = invoices.filter(invoice_type='normal').count()
            hearing_order_count = invoices.filter(invoice_type='hearing').count()

            # SolderingInvoice.invoice_date is DateField, so use date comparison
            soldering_invoices = SolderingInvoice.objects.filter(
                invoice_date__gte=start_datetime.date(),
                invoice_date__lte=end_datetime.date(),
                order__branch_id=branch_id_int,
                is_deleted=False
            )
            soldering_order_count = soldering_invoices.count()

            # Appointment.created_at is DateTimeField
            appointments = Appointment.objects.filter(
                created_at__gte=start_datetime,
                created_at__lt=end_datetime,
                branch_id=branch_id_int,
                is_deleted=False
            )
            channel_count = appointments.count()

            # Amounts - filter by invoice date range AND payment date range
            factory_order_amount = OrderPayment.objects.filter(
                order__invoice__invoice_type='factory',
                order__invoice__invoice_date__gte=start_datetime,
                order__invoice__invoice_date__lt=end_datetime,
                order__branch_id=branch_id_int,
                order__invoice__is_deleted=False,
                payment_date__gte=start_datetime,
                payment_date__lt=end_datetime,
                is_deleted=False
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            normal_order_amount = OrderPayment.objects.filter(
                order__invoice__invoice_type='normal',
                order__invoice__invoice_date__gte=start_datetime,
                order__invoice__invoice_date__lt=end_datetime,
                order__branch_id=branch_id_int,
                order__invoice__is_deleted=False,
                payment_date__gte=start_datetime,
                payment_date__lt=end_datetime,
                is_deleted=False
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            hearing_order_amount = OrderPayment.objects.filter(
                order__invoice__invoice_type='hearing',
                order__invoice__invoice_date__gte=start_datetime,
                order__invoice__invoice_date__lt=end_datetime,
                order__branch_id=branch_id_int,
                order__invoice__is_deleted=False,
                payment_date__gte=start_datetime,
                payment_date__lt=end_datetime,
                is_deleted=False
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            # SolderingPayment.payment_date is DateTimeField
            soldering_order_amount = SolderingPayment.objects.filter(
                order__branch_id=branch_id_int,
                payment_date__gte=start_datetime,
                payment_date__lt=end_datetime,
                is_deleted=False
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            # ChannelPayment.payment_date is DateTimeField
            channel_amount = ChannelPayment.objects.filter(
                appointment__branch_id=branch_id_int,
                appointment__created_at__gte=start_datetime,
                appointment__created_at__lt=end_datetime,
                appointment__is_deleted=False,
                payment_date__gte=start_datetime,
                payment_date__lt=end_datetime,
                is_deleted=False
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            # Expense.created_at is DateTimeField
            expense_amount = Expense.objects.filter(
                branch_id=branch_id_int,
                created_at__gte=start_datetime,
                created_at__lt=end_datetime
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            # ExpenseReturn.created_at is DateTimeField
            expense_return_amount = ExpenseReturn.objects.filter(
                branch_id=branch_id_int,
                created_at__gte=start_datetime,
                created_at__lt=end_datetime
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            return Response({
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
                "Expense_return_amount": expense_return_amount
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)