# views.py
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_date
from ..models import Order
from ..serializers import OrderLiteSerializer
from ..services.pagination_service import PaginationService
from rest_framework.exceptions import ValidationError

class GlassSenderReportView(ListAPIView):
    serializer_class = OrderLiteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationService

    def get_queryset(self):
        branch_id = self.request.query_params.get('branch_id')
        if not branch_id:
            raise ValidationError({"branch_id": "This query parameter is required."})

        queryset = Order.objects.filter(is_deleted=False, branch_id=branch_id)
        user_id = self.request.query_params.get('user_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        invoice_number = self.request.query_params.get('invoice_number')

        if user_id:
            queryset = queryset.filter(issued_by_id=user_id)
        else:
            # Only get orders where issued_by is set (not null)
            queryset = queryset.exclude(issued_by__isnull=True)

        if start_date and end_date:
            queryset = queryset.filter(
                issued_date__date__gte=parse_date(start_date),
                issued_date__date__lte=parse_date(end_date)
            )
        elif start_date:
            queryset = queryset.filter(issued_date__date__gte=parse_date(start_date))
        elif end_date:
            queryset = queryset.filter(issued_date__date__lte=parse_date(end_date))

        if invoice_number:
            queryset = queryset.filter(invoice__invoice_number=invoice_number)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        user_id = request.query_params.get('user_id')
        response = super().list(request, *args, **kwargs)
        if user_id:
            user_total_count = queryset.count()
            if isinstance(response.data, dict) and 'results' in response.data:
                response.data['user_total_count'] = user_total_count
        return response