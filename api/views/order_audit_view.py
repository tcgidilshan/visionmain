# views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from api.models import Invoice, OrderAuditLog, OrderPayment
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.generics import ListAPIView
from ..models import Order,OrderItem,OrderPayment,RefractionDetails,OrderAuditLog,Invoice,RefractionDetailsAuditLog
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import OrderLiteSerializer,OrderSerializer,OrderItemSerializer,OrderPaymentSerializer
from ..services.pagination_service import PaginationService 
from django.db.models import (
    BooleanField,
    Exists,
    OuterRef,
    Q,
    Value,
)
from rest_framework.exceptions import ValidationError
from ..services.time_zone_convert_service import TimezoneConverterService

class OrderDeleteRefundListView(ListAPIView):
    pagination_class = PaginationService
    serializer_class = OrderLiteSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get("status")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
        queryset = Order.all_objects.select_related('customer', 'branch')
        
        # Decide which records to return
        if status_filter == "deactivated":
            queryset = queryset.filter(is_deleted=True, is_refund=False)
            date_field = "deleted_at"
        elif status_filter == "deactivated_refunded":
            queryset = queryset.filter(is_deleted=True, is_refund=True)
            date_field = "refunded_at"
        elif status_filter == "refunded":
            queryset = queryset.filter(is_refund=True, is_deleted=False)
            date_field = "refunded_at"
        else:  # Active or missing
            queryset = queryset.filter(is_deleted=False, is_refund=False)
            date_field = "order_date"
     
        # Date filtering - Fixed to use proper datetime range filtering
        if start_datetime and end_datetime:
            if start_datetime.date() == end_datetime.date():
                # Same day - use datetime range for timezone-aware fields
                filter_kwargs = {f"{date_field}__range": [start_datetime, end_datetime]}
                queryset = queryset.filter(**filter_kwargs)
            else:
                # Different days - use datetime range
                filter_kwargs = {f"{date_field}__range": [start_datetime, end_datetime]}
                queryset = queryset.filter(**filter_kwargs)
        elif start_datetime:
            filter_kwargs = {f"{date_field}__gte": start_datetime}
            queryset = queryset.filter(**filter_kwargs)
        elif end_datetime:
            filter_kwargs = {f"{date_field}__lte": end_datetime}
            queryset = queryset.filter(**filter_kwargs)
        return queryset.order_by("-" + date_field)

class OrderAuditHistoryView(APIView):
    """
    Returns all soft-deleted orders, items, and payments.
    """

    def get(self, request):
        # Get soft-deleted records
        order_id = request.query_params.get("order_id")
        order_logs = OrderAuditLog.objects.all()
        order_items = OrderItem.all_objects.filter(is_deleted=True).order_by('-deleted_at')
        order_payments = OrderPayment.all_objects.filter(is_deleted=True).order_by('-deleted_at')
        refraction_logs = []
        if order_id:
            order_items = order_items.filter(order_id=order_id)
            order_payments = order_payments.filter(order_id=order_id)
            order_logs = order_logs.filter(order_id=order_id)
            # Fetch refraction details audit logs if applicable
            try:
                order = Order.all_objects.select_related('refraction').get(id=order_id)
                if order.refraction:
                    ref_details = RefractionDetails.objects.filter(refraction_id=order.refraction.id).first()
                    if ref_details:
                        refraction_logs = RefractionDetailsAuditLog.objects.filter(
                            refraction_details=ref_details
                        ).order_by("-created_at")
            except Order.DoesNotExist:
                pass
       
        data = {
            # "orders": OrderSerializer(orders, many=True).data,
            "order_items": OrderItemSerializer(order_items, many=True).data,
            "order_payments": OrderPaymentSerializer(order_payments, many=True).data,
        }

        return Response({
            "order_items": OrderItemSerializer(order_items.order_by('-deleted_at'), many=True).data,
            "order_payments": OrderPaymentSerializer(order_payments.order_by('-deleted_at'), many=True).data,
            "order_logs": [
                {
                    "order_id": log.order_id,
                    "field_name": log.field_name,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "user_name": log.user.username if log.user else None,
                    "admin_name": log.admin.username if log.admin else None,
                    "created_at": log.created_at,
                }
                for log in order_logs.order_by('-created_at')
            ],
            "refraction_logs": [
                {
                    "field_name": log.field_name,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "user_name": log.user.username if log.user else None,
                    "admin_name": log.admin.username if log.admin else None,
                    "created_at": log.created_at,
                }
                for log in refraction_logs
            ],
            "invoice_number": Invoice.all_objects.filter(order_id=order_id).values_list('invoice_number', flat=True).first() if order_id else None
        }, status=status.HTTP_200_OK)
class DailyOrderAuditReportView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationService

    # --------------------------------------------------------------------- #
    # helpers
    # --------------------------------------------------------------------- #
    def _parse_range(self):
        """
        Convert ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD to timezone-aware
        datetimes covering **[start, end_of_day]**.  Defaults to “today”.
        """
        start_str = self.request.query_params.get("start_date")
        end_str   = self.request.query_params.get("end_date")

        if not start_str or not end_str:
            today  = timezone.localdate()
            start  = datetime.combine(today, datetime.min.time())
            end    = start + timedelta(days=1)
            return timezone.make_aware(start), timezone.make_aware(end)

        try:
            start = datetime.strptime(start_str, "%Y-%m-%d")
            end   = datetime.strptime(end_str,   "%Y-%m-%d") + timedelta(days=1)
            return timezone.make_aware(start), timezone.make_aware(end)
        except ValueError:
            raise ValidationError("start_date and end_date must be YYYY-MM-DD")

    # --------------------------------------------------------------------- #
    # main queryset
    # --------------------------------------------------------------------- #
    def get_queryset(self):
        start, end = self._parse_range()
        branch_id  = self.request.query_params.get("branch_id")

        # Start with all non-deleted invoices
        qs = Invoice.objects.filter(is_deleted=False)

        # Filter by branch if specified
        if branch_id:
            qs = qs.filter(order__branch_id=branch_id)

        # -- 1️⃣ orders whose *refraction* changed in range ---------------- #
        refraction_sq = RefractionDetailsAuditLog.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            refraction_details__refraction_id=OuterRef("order__refraction_id")
        )
        qs = qs.annotate(has_refraction_change=Exists(refraction_sq))

        # -- 2️⃣ header-level OrderAuditLog -------------------------------- #
        header_sq = OrderAuditLog.objects.filter(
            order_id=OuterRef("order_id"),
            created_at__gte=start,
            created_at__lt=end,
        )
        qs = qs.annotate(order_details=Exists(header_sq))

        # -- 3️⃣ item-level changes (added OR soft-deleted) ---------------- #
        # New rows → rely on `created_at` if you have it; otherwise only deletions
        item_filter = Q(deleted_at__gte=start, deleted_at__lt=end)
        if hasattr(OrderItem, "created_at"):
            item_filter |= Q(created_at__gte=start, created_at__lt=end)

        item_sq = OrderItem.all_objects.filter(
            order_id=OuterRef("order_id")
        ).filter(item_filter)
        qs = qs.annotate(order_item=Exists(item_sq))

        # -- 4️⃣ payment-level changes ------------------------------------- #
        pay_sq = OrderPayment.all_objects.filter(
            order_id=OuterRef("order_id")
        ).filter(
            Q(payment_date__gte=start, payment_date__lt=end) |
            Q(deleted_at__gte=start,  deleted_at__lt=end)
        )
        qs = qs.annotate(order_payment=Exists(pay_sq))

        # Filter to only include invoices with at least one type of change
        qs = qs.filter(
            Q(has_refraction_change=True) |
            Q(order_details=True) |
            Q(order_item=True) |
            Q(order_payment=True)
        )
        
        return qs.order_by("-invoice_date").distinct()

    # --------------------------------------------------------------------- #
    # response formatter – flatten to plain dicts
    # --------------------------------------------------------------------- #
    def list(self, request, *args, **kwargs):
        base_qs = self.get_queryset().values(
            "invoice_number",
            "order_id",
            "order_details",
            "order_item",
            "order_payment",
        ).annotate(
            refraction_details=Value(True, output_field=BooleanField())
        )

        # pagination works on list-of-dicts just fine
        page = self.paginate_queryset(list(base_qs))
        if page is not None:
            return self.get_paginated_response(page)

        return Response(list(base_qs))
