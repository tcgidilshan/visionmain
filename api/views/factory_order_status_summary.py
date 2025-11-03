from django.db.models import Count, Subquery, OuterRef
from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import Order, OrderProgress


class FactoryOrderStatusSummaryView(APIView):
    def get(self, request):
        branch_id = request.GET.get('branch_id')
        
        # Filter orders with invoice_type='factory'
        orders = Order.objects.filter(invoice__invoice_type='factory')
        
        if branch_id:
            orders = orders.filter(branch_id=branch_id)
        
        # Subquery to get the latest progress status for each order
        latest_progress = OrderProgress.objects.filter(
            order=OuterRef('pk')
        ).order_by('-changed_at').values('progress_status')[:1]
        
        # Annotate each order with its last status
        orders_with_status = orders.annotate(
            last_status=Subquery(latest_progress)
        )
        
        # Count orders by their last status
        status_counts = orders_with_status.values('last_status').annotate(count=Count('id'))
        
        # Possible statuses
        possible_statuses = [
            'received_from_customer',
            'issue_to_factory',
            'received_from_factory',
            'issue_to_customer'
        ]
        
        # Initialize summary with 0 for all statuses
        summary = {status: 0 for status in possible_statuses}
        
        # Update with actual counts
        for item in status_counts:
            if item['last_status'] in summary:
                summary[item['last_status']] = item['count']
        
        return Response(summary)