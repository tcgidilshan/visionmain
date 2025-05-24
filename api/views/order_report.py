from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from ..models import Order

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from ..models import Order

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from ..models import Order
from ..services.pagination_service import PaginationService
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from ..models import Order, Invoice
from ..serializers import InvoiceSearchSerializer
from ..services.pagination_service import PaginationService

class FittingStatusReportView(APIView):
    permission_classes = [IsAuthenticated]
    VALID_STATUSES = {'fitting_ok', 'not_fitting', 'damage'}

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

        # Fitting status filter
        if fitting_status:
            if fitting_status not in self.VALID_STATUSES:
                return Response({'error': f"Invalid fitting_status. Choose one of: {', '.join(self.VALID_STATUSES)}"}, status=400)
            orders_qs = orders_qs.filter(fitting_status=fitting_status)

        # --- ONLY ORDERS WITH FACTORY INVOICE ---
        factory_order_ids = Invoice.objects.filter(
            is_deleted=False,
            invoice_type='factory',
            order__in=orders_qs
        ).values_list("order_id", flat=True)

        orders_qs = orders_qs.filter(id__in=factory_order_ids)

        # --- SUMMARY METRICS (all for this branch and filters) ---
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

        # --- PAGINATE THE FACTORY INVOICE LIST ---
        invoice_qs = Invoice.objects.filter(
            order__in=orders_qs,
            is_deleted=False,
            invoice_type='factory'
        ).order_by('-invoice_date')
        paginator = PaginationService()
        paginated_invoices = paginator.paginate_queryset(invoice_qs, request)
        serialized_invoices = InvoiceSearchSerializer(paginated_invoices, many=True).data

        # Combine metrics and results in paginated response
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