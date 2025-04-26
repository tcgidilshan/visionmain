from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from ..models import Invoice, Appointment

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

        if not date_str or not branch_id:
            return Response(
                {"error": "Both 'date' and 'branch_id' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            given_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Please use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 🔹 Step 2: Query Counts

            # Factory orders
            factory_order_count = Invoice.objects.filter(
                invoice_date__date=given_date,
                order__branch_id=branch_id,
                invoice_type='factory'
            ).count()

            # Normal orders
            normal_order_count = Invoice.objects.filter(
                invoice_date__date=given_date,
                order__branch_id=branch_id,
                invoice_type='normal'
            ).count()

            # Channel Appointments
            channel_count = Appointment.objects.filter(
                date=given_date,
                branch_id=branch_id,
                channel_no__isnull=False
            ).count()

            # 🔹 Step 3: Return the Response
            return Response({
                "date": str(given_date),
                "branch_id": branch_id,
                "factory_order_count": factory_order_count,
                "normal_order_count": normal_order_count,
                "channel_count": channel_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
