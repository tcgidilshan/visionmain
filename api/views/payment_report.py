from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Q, F
from api.models import Branch, OrderPayment, ChannelPayment, SolderingPayment
from api.services.time_zone_convert_service import TimezoneConverterService

class PaymentSummaryReportView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        payment_filter = request.query_params.get('payment')  # Optional: filter by payment method

        # Get timezone-aware datetimes
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
        if not start_datetime or not end_datetime:
            return Response({"error": "Invalid or missing date(s). Use YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare payment method filter
        payment_methods = ['cash', 'credit_card', 'online_transfer']
        if payment_filter and payment_filter in payment_methods:
            payment_methods = [payment_filter]

        # Get all branches
        branches = Branch.objects.all()
        payments_data = []
        sub_total_payments = 0

        for branch in branches:
            branch_totals = {pm: 0 for pm in ['cash', 'credit_card', 'online_transfer']}

            # OrderPayment (sales)
            order_payments = OrderPayment.objects.filter(
                order__branch=branch,
                payment_date__range=(start_datetime, end_datetime),
                is_deleted=False,
                transaction_status='success',
                payment_method__in=payment_methods
            ).values('payment_method').annotate(total=Sum('amount'))
            for op in order_payments:
                branch_totals[op['payment_method']] += float(op['total'] or 0)

            # ChannelPayment (appointments)
            channel_payments = ChannelPayment.objects.filter(
                appointment__branch=branch,
                payment_date__range=(start_datetime, end_datetime),
                is_deleted=False,
                payment_method__in=payment_methods
            ).values('payment_method').annotate(total=Sum('amount'))
            for cp in channel_payments:
                branch_totals[cp['payment_method']] += float(cp['total'] or 0)

            # SolderingPayment (soldering orders)
            soldering_payments = SolderingPayment.objects.filter(
                order__branch=branch,
                payment_date__range=(start_datetime, end_datetime),
                is_deleted=False,
                transaction_status='completed',
                payment_method__in=payment_methods
            ).values('payment_method').annotate(total=Sum('amount'))
            for sp in soldering_payments:
                branch_totals[sp['payment_method']] += float(sp['total'] or 0)

            branch_total = sum(branch_totals.values())
            sub_total_payments += branch_total

            payments_data.append({
                'branch_id': branch.id,
                'branch_name': branch.branch_name,
                'total_cash': branch_totals['cash'],
                'total_card': branch_totals['credit_card'],
                'total_online_transfer': branch_totals['online_transfer'],
            })

        return Response({
            'payments': payments_data,
            'sub_total_payments': sub_total_payments
        }, status=status.HTTP_200_OK)