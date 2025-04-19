# views/channel_transfer_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.channel_transfer_service import ChannelTransferService
from ..serializers import AppointmentSerializer

class ChannelTransferView(APIView):
    def post(self, request):
        data = request.data

        appointment_id = data.get("appointment_id")
        new_doctor_id = data.get("new_doctor_id")  # Optional
        new_date = data.get("new_date")
        new_time = data.get("new_time")
        branch_id = data.get("branch_id")

        # Validation
        if not all([appointment_id, new_date, new_time, branch_id]):
            return Response({"error": "appointment_id, new_date, new_time, branch_id are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            # Transfer logic
            updated_appointment = ChannelTransferService.transfer_appointment(
                appointment_id,
                new_doctor_id,
                new_date,
                new_time,
                branch_id
            )

            return Response({
                "message": "Appointment successfully transferred.",
                "appointment": AppointmentSerializer(updated_appointment).data
            }, status=status.HTTP_200_OK)

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
