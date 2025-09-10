# views/channel_repayment_view.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import Appointment
from ..services.channel_payment_service import ChannelPaymentService
from ..serializers import MultipleRepaymentSerializer,ChannelPaymentSerializer

class ChannelRepaymentView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = MultipleRepaymentSerializer(data=request.data)
        if serializer.is_valid():
            results = []

            for payment_data in serializer.validated_data['payments']:
                try:
                    appointment = Appointment.objects.get(id=payment_data['appointment_id'])

                    payment = ChannelPaymentService.create_repayment(
                        appointment=appointment,
                        amount=payment_data.get('amount'),
                        method=payment_data['payment_method'],
                        payment_method_bank=payment_data.get('payment_method_bank')  # Use .get() instead of direct access
                    )

                    results.append({
                        "success": True,
                        "payment": ChannelPaymentSerializer(payment).data
                    })

                except Appointment.DoesNotExist:
                    results.append({
                        "success": False,
                        "error": f"Appointment ID {payment_data['appointment_id']} not found."
                    })

                except ValueError as e:
                    results.append({
                        "success": False,
                        "error": str(e)
                    })

            return Response({
                "message": "Payment processing result",
                "results": results
            }, status=status.HTTP_207_MULTI_STATUS)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
