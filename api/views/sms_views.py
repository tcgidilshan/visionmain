from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import SMSTemplate, SMSLog
from ..serializers import SMSSendSerializer, SMSTemplateSerializer, SMSLogSerializer
from ..services.send_sms_service import SMSService
from ..services.pagination_service import PaginationService
from ..services.time_zone_convert_service import TimezoneConverterService


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


class SMSTemplateListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset           = SMSTemplate.objects.all().order_by('template_type', '-active', '-created_at')
    serializer_class   = SMSTemplateSerializer


class SMSTemplateRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset           = SMSTemplate.objects.all()
    serializer_class   = SMSTemplateSerializer


class SMSLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = SMSLogSerializer
    pagination_class   = PaginationService

    def get_queryset(self):
        qs = SMSLog.objects.all()
        p  = self.request.query_params

        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('template_type'):
            qs = qs.filter(template_type=p['template_type'])
        if p.get('mobile_number'):
            qs = qs.filter(mobile_number__icontains=p['mobile_number'])
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(
            p.get('start_date'), p.get('end_date')
        )
        if start_datetime:
            qs = qs.filter(sent_at__gte=start_datetime)
        if end_datetime:
            qs = qs.filter(sent_at__lte=end_datetime)

        return qs
