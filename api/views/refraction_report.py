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

        # Get refractions that do not have any associated orders
        refractions = Refraction.objects.annotate(
            num_orders=Count('order')
        ).filter(
            num_orders=0,
            created_at__range=(start_datetime, end_datetime)
        ).select_related('patient', 'branch')

        if branch_id:
            refractions = refractions.filter(branch_id=branch_id)

        data = []
        for r in refractions:
            data.append({
                'id': r.id,
                'refraction_number': r.refraction_number,
                'patient_name': r.patient.name if r.patient else None,
                'patient_mobile': r.patient.phone_number if r.patient else None,
                'branch_name': r.branch.branch_name if r.branch else None,
                'created_at': r.created_at.isoformat(),
            })

        return Response(data)