# views.py

from rest_framework.generics import ListAPIView
from ..models import Order
from ..serializers import OrderLiteSerializer
from ..services.pagination_service import PaginationService  # Use your existing paginator

class OrderDeleteRefundListView(ListAPIView):
    pagination_class = PaginationService
    serializer_class = OrderLiteSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get("status")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
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

        # Date filtering
        if start_date and end_date:
            if start_date == end_date:
                filter_kwargs = {f"{date_field}__date": start_date}
                queryset = queryset.filter(**filter_kwargs)
            else:
                filter_kwargs = {f"{date_field}__date__range": [start_date, end_date]}
                queryset = queryset.filter(**filter_kwargs)
        elif start_date:
            filter_kwargs = {f"{date_field}__date__gte": start_date}
            queryset = queryset.filter(**filter_kwargs)
        elif end_date:
            filter_kwargs = {f"{date_field}__date__lte": end_date}
            queryset = queryset.filter(**filter_kwargs)

        return queryset.order_by("-" + date_field)
