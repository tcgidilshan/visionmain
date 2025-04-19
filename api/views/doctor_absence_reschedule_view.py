from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from ..services.doctor_absence_service import DoctorAbsenceService

class DoctorAbsenceRescheduleView(APIView):
    """
    API endpoint to reschedule all appointments for a doctor
    if they are absent between a given date range.
    """

    def post(self, request, *args, **kwargs):
        doctor_id = request.data.get('doctor_id')
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')

        # Validate input
        if not doctor_id or not from_date or not to_date:
            return Response({
                "error": "doctor_id, from_date, and to_date are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Parse dates to proper format
            from_date_obj = parse_date(from_date)
            to_date_obj = parse_date(to_date)

            if not from_date_obj or not to_date_obj:
                return Response({
                    "error": "Invalid date format. Use YYYY-MM-DD."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Call service to reschedule
            result = DoctorAbsenceService.reschedule_appointments(
                doctor_id=doctor_id,
                from_date=from_date_obj,
                to_date=to_date_obj
            )

            return Response({
                "message": f"{result['count']} appointments were rescheduled.",
                "rescheduled_appointments": result["appointments"]
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
