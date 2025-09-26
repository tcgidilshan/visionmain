from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from api.models import (
    Branch, Order, OrderPayment, Invoice, Appointment, ChannelPayment, 
    SolderingOrder, SolderingPayment, Expense, OtherIncome, BankDeposit,
    SafeTransaction, CustomUser, MntOrder, HearingOrderItemService
)
from api.services.time_zone_convert_service import TimezoneConverterService
from ..serializers import PaymentReportSerializer

class DailyMoneyReportView(APIView):
    permission_classes = [IsAuthenticated]   # restrict to logged-in users

    def get(self, request, *args, **kwargs):
        # Optional filters (date range, branch, etc.)
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        filters = {"transaction_status": "success", "is_deleted": False}
        if start_date and end_date:
            filters["payment_date__range"] = [start_date, end_date]

        queryset = (
            OrderPayment.objects.filter(**filters)
            .values(
                "payment_method_bank__id",
                "payment_method_bank__name",
                 "payment_method",  
                "order__invoice__invoice_type",
                "order__refraction_id",  # Keep only refraction ID
            )
            .annotate(total_amount=Sum("amount"))
            .order_by("payment_method_bank__name", "order__invoice__invoice_type")
        )

        serializer = PaymentReportSerializer(queryset, many=True)
        return Response(serializer.data)