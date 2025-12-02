# refraction_report.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from ..models import Refraction
from ..services.time_zone_convert_service import TimezoneConverterService


class RefractionReportView(APIView):
    def get(self, request):
        start_date = request.query_params.get('date_start')
        end_date = request.query_params.get('date_end')
        branch_id = request.query_params.get('branch_id')

        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)

        if not start_datetime or not end_datetime:
            return Response({"error": "Invalid date range"}, status=400)

        # Base queryset with counts
        refractions_with_counts = Refraction.objects.annotate(
            num_orders=Count('order')
        ).filter(
            created_at__range=(start_datetime, end_datetime)
        ).select_related('patient', 'branch')

        if branch_id:
            refractions_with_counts = refractions_with_counts.filter(branch_id=branch_id)

        # Get refractions that do not have any associated orders
        refractions_without_orders = refractions_with_counts.filter(num_orders=0)

        # Get refractions that have orders
        refractions_with_orders = refractions_with_counts.filter(num_orders__gt=0)

        # Calculate totals
        total_refractions = refractions_with_counts.count()
        total_with_orders = refractions_with_orders.count()
        total_without_orders = refractions_without_orders.count()

        data = []
        for r in refractions_without_orders:
            data.append({
                'id': r.id,
                'refraction_number': r.refraction_number,
                'patient_name': r.patient.name if r.patient else None,
                'patient_mobile': r.patient.phone_number if r.patient else None,
                'branch_name': r.branch.branch_name if r.branch else None,
                'created_at': r.created_at.isoformat(),
            })

        # Build response with summary
        response_data = {
            'summary': {
                'total_refractions': total_refractions,
                'refractions_with_orders': total_with_orders,
                'refractions_without_orders': total_without_orders,
            },
            'refractions_without_orders': data
        }

        return Response(response_data)