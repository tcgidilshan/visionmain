from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from ..services.finance_summary_service import DailyFinanceSummaryService
from datetime import datetime

class DailyFinanceSummaryView(APIView):
    """
    Get the daily cash summary report for a specific branch and date.
    """
    def get(self, request):
        branch_id = request.query_params.get('branch')
        date_str = request.query_params.get('date')  # Optional

        if not branch_id:
            return Response({"error": "branch parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Parse date or default to today
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.localdate()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        try:
            summary = DailyFinanceSummaryService.get_summary(branch_id=int(branch_id), date=date)
            return Response(summary, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
