from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.cross_branch_payment_service import CrossBranchPaymentService


class CrossBranchPaymentReportView(APIView):
    """
    API View to get cross-branch payment report.
    Shows payments received at a specific branch for factory invoices.
    
    Query Parameters:
    - branch_id (required): Branch ID to filter payments
    - start_date (optional): Start date in format 'YYYY-MM-DD'
    - end_date (optional): End date in format 'YYYY-MM-DD'
    """

    def get(self, request, *args, **kwargs):
        try:
            # Get required parameter
            branch_id = request.query_params.get('branch_id')
            
            if not branch_id:
                return Response(
                    {
                        'status': 'error',
                        'message': 'branch_id query parameter is required.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get optional date parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # Get report from service
            report_data = CrossBranchPaymentService.get_cross_branch_payment_report(
                branch_id=branch_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Check if service returned an error
            if report_data.get('status') == 'error':
                return Response(report_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response(
                {
                    'data': report_data
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    'status': 'error',
                    'message': f'An error occurred: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
