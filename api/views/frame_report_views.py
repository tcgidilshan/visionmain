# views/frame_report_view.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.frame_report_service import generate_frames_report

class FrameReportView(APIView):
    """
    API view to retrieve a frames sold report within a date range.
    """

    def get(self, request, *args, **kwargs):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response(
                {"detail": "start_date and end_date query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            report_data = generate_frames_report(start_date, end_date)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(report_data, status=status.HTTP_200_OK)

class FrameBrandReportView(APIView):
    """
    API view to retrieve a brand-wise frame report with stock and sales data.
    Optional query parameter: initial_branch - filter frames by initial branch ID
    """
    def get(self, request, *args, **kwargs):
        try:
            from ..services.frame_report_service import generate_brand_wise_report
            
            # Get initial_branch from query parameters if provided
            initial_branch_id = request.query_params.get('initial_branch')
            
            report_data = generate_brand_wise_report(initial_branch_id=initial_branch_id)
            return Response({
                "data": report_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
