from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..serializers import SMSSendSerializer
from ..services.send_sms_service import SMSService


class SendSMSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SMSSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mobile_numbers = serializer.validated_data['mobile_numbers']
        message = serializer.validated_data['message']
        source_address = serializer.validated_data.get('source_address') or None

        result = SMSService.send_sms(mobile_numbers, message, source_address)
        return Response(result, status=status.HTTP_200_OK)
