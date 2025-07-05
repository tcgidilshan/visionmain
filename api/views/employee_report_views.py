from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging
from django.utils import timezone

from api.services.employee_report_service import EmployeeReportService


logger = logging.getLogger(__name__)


class EmployeeHistoryReportView(APIView):
    """
    API View for generating employee history reports based on sales performance.
    
    This view handles the generation of reports showing employee sales performance
    including frames, lenses, factory orders, and normal orders within a date range.
    """
    
    def get(self, request):
        """
        GET endpoint to retrieve employee history report.
        
        Query Parameters:
            start_date (str): Start date in YYYY-MM-DD format (required)
            end_date (str): End date in YYYY-MM-DD format (required)
            employee_code (str, optional): Specific employee code to filter by
            branch_id (int, optional): Branch ID to filter by
            include_summary (bool): Whether to include summary statistics
            
        Returns:
            JSON response with employee performance data
        """
        
        try:
            # Extract query parameters
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            employee_code = request.GET.get('employee_code')
            branch_id = request.GET.get('branch_id')
            include_summary = request.GET.get('include_summary', 'false').lower() == 'true'
            
            # Validate required parameters
            if not all([start_date, end_date]):
                return Response({
                    'error': 'Missing required parameters',
                    'details': 'start_date and end_date are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate and convert dates
            try:
                start_dt, end_dt = EmployeeReportService.validate_date_range(
                    start_date, end_date
                )
            except ValueError as e:
                return Response({
                    'error': 'Invalid date format',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate branch_id if provided
            branch_id_int = None
            if branch_id:
                try:
                    branch_id_int = int(branch_id)
                    if branch_id_int <= 0:
                        raise ValueError("Branch ID must be a positive integer")
                except ValueError:
                    return Response({
                        'error': 'Invalid branch_id',
                        'details': 'Branch ID must be a positive integer'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate report
            employees_data = EmployeeReportService.get_employee_history_report(
                start_dt, end_dt, employee_code, branch_id_int
            )
            
            # Prepare response
            response_data = {
                'success': True,
                'data': {
                    'employees': employees_data,
                    'criteria': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'employee_code': employee_code,
                        'branch_id': branch_id_int
                    },
                    'count': len(employees_data),
                    'generated_at': timezone.now().isoformat()
                }
            }
            
            # Include summary if requested
            if include_summary:
                summary_data = EmployeeReportService.get_report_summary(
                    start_dt, end_dt, branch_id_int
                )
                response_data['data']['summary'] = summary_data
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating employee history report: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'details': 'An error occurred while generating the report'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)