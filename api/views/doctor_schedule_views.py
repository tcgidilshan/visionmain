from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.doctor_schedule_service import DoctorScheduleService
from ..serializers import ScheduleSerializer
from ..models import Schedule

class DoctorScheduleCreateView(APIView):
    def post(self, request):
        doctor_id = request.data.get("doctor_id")
        date = request.data.get("date")
        start_time = request.data.get("start_time")
        branch = request.data.get("branch_id")

        if not all([doctor_id, date, start_time, branch]):
            return Response({"error": "doctor_id, date, start_time, branch_id are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        schedule, created = DoctorScheduleService.add_arrival_day(
            doctor_id, date, start_time, branch
        )

        return Response(
            {
                "message": "Schedule created" if created else "Already exists",
                "schedule": ScheduleSerializer(schedule).data
            },
            status=status.HTTP_201_CREATED
        )

class DoctorUpcomingScheduleView(APIView):
    def get(self, request, doctor_id):
        branch_id = request.query_params.get("branch_id")
        schedules = DoctorScheduleService.get_upcoming_arrival_days(doctor_id, branch_id)
        return Response(ScheduleSerializer(schedules, many=True).data)
