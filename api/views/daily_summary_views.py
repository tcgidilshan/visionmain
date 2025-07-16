from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from ..models import ChannelPayment, Invoice, Appointment, Order
from ..services.time_zone_convert_service import TimezoneConverterService

class DailySummaryView(APIView):
    """
    API to get daily counts:
    - Total Factory Orders
    - Total Normal Orders
    - Total Channel Appointments
    Filtered by branch and date.
    """

    def post(self, request, *args, **kwargs):
        # 🔹 Step 1: Extract date and branch_id
        date_str = request.data.get("date")
        branch_id = request.data.get("branch_id")

        if not branch_id:
            return Response(
                {"error": "branch_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use TimezoneConverterService for consistent date handling
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(date_str, date_str)
        
        if start_datetime is None:
            return Response(
                {"error": "Invalid date format. Please use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        given_date = start_datetime.date()

        try:
            # 🔹 Step 2: Query Counts using timezone-aware datetime range

            # Factory orders
            factory_order_count = Order.objects.filter(
                order_date__gte=start_datetime,
                order_date__lte=end_datetime,
                branch_id=branch_id,
                invoice__invoice_type='factory'
            ).count()

            # Normal orders
            normal_order_count = Order.objects.filter(
                order_date__gte=start_datetime,
                order_date__lte=end_datetime,
                branch_id=branch_id,
                invoice__invoice_type='normal'
            ).count()

            # Channel Appointments with payment received on the given date
            channel_payment_count = Appointment.objects.filter(
                branch_id=branch_id,
                created_at__lte=end_datetime,
                created_at__gte=start_datetime,
          
            ).count()
        

            # 🔹 Step 3: Return the Response
            return Response({
                "date": str(given_date),
                "branch_id": branch_id,
                "factory_order_count": factory_order_count,
                "normal_order_count": normal_order_count,
                "channel_count": channel_payment_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
