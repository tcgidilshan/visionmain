from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from ..models import Order, Invoice
from ..serializers import InvoiceSearchSerializer,MntOrderSerializer
from ..services.pagination_service import PaginationService
from ..models import MntOrder  
from django.db.models import Count, Sum
from decimal import Decimal
from rest_framework import status
from ..services.time_zone_convert_service import TimezoneConverterService

class FittingStatusReportView(APIView):
    permission_classes = [IsAuthenticated]
    VALID_STATUSES = {'fitting_ok', 'not_fitting', 'damage', 'Pending'}

    def get(self, request):
        branch_id = request.query_params.get('branch_id')
        if not branch_id:
            return Response({'error': 'branch_id parameter is required.'}, status=400)

        date_str = request.query_params.get('date')
        fitting_status = request.query_params.get('fitting_status')

        orders_qs = Order.objects.filter(is_deleted=False, branch_id=branch_id)

        # Date filter
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                orders_qs = orders_qs.filter(order_date__date=target_date)
            except ValueError:
                return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=400)

        # Fitting status filter: skip "Pending" by default
        if fitting_status is not None and fitting_status.strip() != "":
            orders_qs = orders_qs.filter(fitting_status=fitting_status)
        else:
            orders_qs = orders_qs.exclude(fitting_status="Pending")

        # Only orders with factory invoice
        factory_order_ids = Invoice.objects.filter(
            is_deleted=False,
            invoice_type='factory',
            order__in=orders_qs
        ).values_list("order_id", flat=True)
        orders_qs = orders_qs.filter(id__in=factory_order_ids)

        # Metrics & pagination as before...
        damage_count = orders_qs.filter(fitting_status='damage').count()
        fitting_ok_count = orders_qs.filter(fitting_status='fitting_ok').count()
        fitting_not_ok_count = orders_qs.filter(fitting_status='not_fitting').count()
        stock_lens_orders_count = orders_qs.filter(
            order_items__is_non_stock=False,
            order_items__is_deleted=False
        ).distinct().count()
        non_stock_order_ids = [
            o.id for o in orders_qs if not o.order_items.filter(is_non_stock=False, is_deleted=False).exists()
        ]
        non_stock_lens_orders_count = len(non_stock_order_ids)

        invoice_qs = Invoice.objects.filter(
            order__in=orders_qs,
            is_deleted=False,
            invoice_type='factory'
        ).order_by('-invoice_date')
        paginator = PaginationService()
        paginated_invoices = paginator.paginate_queryset(invoice_qs, request)
        serialized_invoices = InvoiceSearchSerializer(paginated_invoices, many=True).data

        result = {
            "branch_id": branch_id,
            "damage_count": damage_count,
            "fitting_ok_count": fitting_ok_count,
            "fitting_not_ok_count": fitting_not_ok_count,
            "total_stock_lens_orders": stock_lens_orders_count,
            "total_non_stock_lens_orders": non_stock_lens_orders_count,
            "orders": serialized_invoices,  # paginated
        }
        return paginator.get_paginated_response(result)

class MntOrderReportView(APIView):
    """
    Returns a per-branch snapshot of MNT orders, optionally filtered by date
    (uses created_at date; NOT time-zone aware for performance - adjust if needed).

    Query params
    ------------
    branch_id   (int, required)
    start_date  (YYYY-MM-DD, optional) → filters by `created_at` date portion
    end_date    (YYYY-MM-DD, optional) → filters by `created_at` date portion
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return Response(
                {"error": "branch_id parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # ✧✧ Base queryset — eager-load FKs to avoid N+1 hits ✧✧
        qs = (
            MntOrder.objects
            .select_related("order", "branch", "user", "admin")
            .filter(branch_id=branch_id)
        )

        # --- Optional date range filter -------------------------------------
        if start_date or end_date:
            try:
                # Use TimezoneConverterService to handle timezone conversion
                start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
                
                if start_datetime and end_datetime:
                    # Filter by datetime range (timezone-aware)
                    qs = qs.filter(created_at__range=(start_datetime, end_datetime))
                elif start_datetime:
                    # Only start date provided
                    qs = qs.filter(created_at__gte=start_datetime)
                elif end_datetime:
                    # Only end date provided
                    qs = qs.filter(created_at__lte=end_datetime)
                    
            except ValueError:
                return Response(
                    {"error": "Invalid date format, use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ========== Metrics ==================================================
        # DB-side aggregation keeps it transactional-safe & fast
        aggregates = qs.aggregate(
            total_mnt_orders=Count("id"),
            total_mnt_price=Sum("mnt_price"),
        )
        total_mnt_orders   = aggregates["total_mnt_orders"]
        total_mnt_price    = aggregates["total_mnt_price"] or Decimal("0.00")

        # ------- Pagination / serialization ---------------------------------
        paginator = PaginationService()
        paginated_qs = paginator.paginate_queryset(qs.order_by("-created_at"), request)
        serialized   = MntOrderSerializer(paginated_qs, many=True).data

        payload = {
            "branch_id":               int(branch_id),
            "start_date":                  start_date,
            "end_date":                  end_date,
            "total_mnt_orders":        total_mnt_orders,
            "total_mnt_price":         total_mnt_price,
            "orders":                  serialized,   # paginated slice
        }
        return paginator.get_paginated_response(payload)