from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.services.channel_report_service import ChannelReportService

class ChannelReportView(APIView):

    def get(self, request):
        payment_date = request.query_params.get("payment_date")
        branch_id = request.query_params.get("branch_id")

        if not payment_date or not branch_id:
            return Response({"error": "payment_date and branch_id are required."}, status=400)

        try:
            report_data = ChannelReportService.get_channel_payments_by_date_and_branch(payment_date, branch_id)
            return Response(report_data, status=200)
        except Exception as e:
            return Response({"error": f"Something went wrong: {str(e)}"}, status=500)
