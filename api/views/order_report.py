from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
# from .models import Order

class FittingStatusReportView(APIView):
    permission_classes = [IsAuthenticated]  # //TODO Secure with role-based check if required

    # def get(self, request):
    #     date_str = request.query_params.get('date')
    #     if not date_str:
    #         return Response({'error': 'Date parameter is required'}, status=400)
    #     try:
    #         target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    #     except ValueError:
    #         return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=400)
        
    #     orders_qs = Order.objects.filter(
    #         is_deleted=False,
    #         order_date__date=target_date
    #     )
        
    #     # Fitting status counts
    #     damage_count = orders_qs.filter(fitting_status='damage').count()
    #     fitting_ok_count = orders_qs.filter(fitting_status='fitting_ok').count()
    #     fitting_not_ok_count = orders_qs.filter(fitting_status='not_fitting').count()
        
    #     # Stock lens orders (at least one item is stock)
    #     stock_lens_orders_count = orders_qs.filter(
    #         order_items__is_non_stock=False,
    #         order_items__is_deleted=False
    #     ).distinct().count()

    #     # Non-stock lens orders (all items are non-stock)
    #     non_stock_order_ids = [
    #         o.id for o in orders_qs if not o.order_items.filter(is_non_stock=False, is_deleted=False).exists()
    #     ]
    #     non_stock_lens_orders_count = len(non_stock_order_ids)

    #     return Response({
    #         "date": str(target_date),
    #         "damage_count": damage_count,
    #         "fitting_ok_count": fitting_ok_count,
    #         "fitting_not_ok_count": fitting_not_ok_count,
    #         "total_stock_lens_orders": stock_lens_orders_count,
    #         "total_non_stock_lens_orders": non_stock_lens_orders_count,
    #     })
