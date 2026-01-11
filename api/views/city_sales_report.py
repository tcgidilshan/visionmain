from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.db.models.functions import Lower, Coalesce
from django.db.models import Value
from collections import defaultdict
from ..models import Order, Invoice, Appointment, SolderingOrder, Patient
from ..services.time_zone_convert_service import TimezoneConverterService


class CitySalesReportView(APIView):
    """
    Optimized city-wise sales count report.
    Uses aggregation queries to avoid N+1 problem and improve performance.
    
    Performance: O(1) database queries (5 total) regardless of city count.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET request to retrieve city-wise sales report.
        
        Query Parameters:
        - branch_id: Branch ID to filter (required)
        - start_date: Start date in 'YYYY-MM-DD' format (optional)
        - end_date: End date in 'YYYY-MM-DD' format (optional)
        """
        # Get and validate query parameters
        branch_id = request.GET.get('branch_id')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if not branch_id:
            return Response(
                {"error": "branch_id is required"}, 
                status=400
            )

        # Convert dates to timezone-aware datetime objects
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(
            start_date, end_date
        )

        if start_datetime is None or end_datetime is None:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                status=400
            )

        # MAP PHASE: Execute 5 aggregated queries (one per order type)
        # Each query groups by city and returns counts in a single database call
        
        # 1. Aggregate factory orders by city
        factory_orders = Order.objects.filter(
            branch_id=branch_id,
            order_date__range=(start_datetime, end_datetime),
            is_deleted=False,
            invoice__invoice_type='factory'
        ).annotate(
            city_lower=Lower(Coalesce('customer__city', Value('unknown')))
        ).values('city_lower').annotate(
            count=Count('id')
        )

        # 2. Aggregate normal orders by city
        normal_orders = Order.objects.filter(
            branch_id=branch_id,
            order_date__range=(start_datetime, end_datetime),
            is_deleted=False,
            invoice__invoice_type='normal'
        ).annotate(
            city_lower=Lower(Coalesce('customer__city', Value('unknown')))
        ).values('city_lower').annotate(
            count=Count('id')
        )

        # 3. Aggregate hearing orders by city
        hearing_orders = Order.objects.filter(
            branch_id=branch_id,
            order_date__range=(start_datetime, end_datetime),
            is_deleted=False,
            invoice__invoice_type='hearing'
        ).annotate(
            city_lower=Lower(Coalesce('customer__city', Value('unknown')))
        ).values('city_lower').annotate(
            count=Count('id')
        )

        # 4. Aggregate appointments (channels) by city
        channels = Appointment.objects.filter(
            branch_id=branch_id,
            created_at__range=(start_datetime, end_datetime),
            is_deleted=False
        ).annotate(
            city_lower=Lower(Coalesce('patient__city', Value('unknown')))
        ).values('city_lower').annotate(
            count=Count('id')
        )

        # 5. Aggregate soldering orders by city
        soldering_orders = SolderingOrder.objects.filter(
            branch_id=branch_id,
            order_date__range=(start_datetime.date(), end_datetime.date()),
            is_deleted=False
        ).annotate(
            city_lower=Lower(Coalesce('patient__city', Value('unknown')))
        ).values('city_lower').annotate(
            count=Count('id')
        )

        # REDUCE PHASE: Merge all results using hash map (O(n) time complexity)
        city_data = defaultdict(lambda: {
            'factory_orders': 0,
            'normal_orders': 0,
            'hearing_orders': 0,
            'channels': 0,
            'soldering': 0,
            'total_count': 0
        })

        # Merge factory orders
        for item in factory_orders:
            city = item['city_lower']
            city_data[city]['factory_orders'] = item['count']
            city_data[city]['total_count'] += item['count']

        # Merge normal orders
        for item in normal_orders:
            city = item['city_lower']
            city_data[city]['normal_orders'] = item['count']
            city_data[city]['total_count'] += item['count']

        # Merge hearing orders
        for item in hearing_orders:
            city = item['city_lower']
            city_data[city]['hearing_orders'] = item['count']
            city_data[city]['total_count'] += item['count']

        # Merge channels
        for item in channels:
            city = item['city_lower']
            city_data[city]['channels'] = item['count']
            city_data[city]['total_count'] += item['count']

        # Merge soldering orders
        for item in soldering_orders:
            city = item['city_lower']
            city_data[city]['soldering'] = item['count']
            city_data[city]['total_count'] += item['count']

        # Build final report list
        city_report = [
            {
                'city': city,
                **data
            }
            for city, data in city_data.items()
        ]

        # Sort by total_count descending (O(n log n))
        city_report.sort(key=lambda x: x['total_count'], reverse=True)

        return Response({
            'branch_id': branch_id,
            'start_date': start_date or 'today',
            'end_date': end_date or 'today',
            'cities': city_report,
            'total_cities': len(city_report),
            'performance_info': {
                'total_queries': 5,
                'optimization': 'aggregated'
            }
        })
