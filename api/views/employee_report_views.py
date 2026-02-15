from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging
from django.utils import timezone

from api.services.employee_report_service import EmployeeReportService
from api.services.time_zone_convert_service import TimezoneConverterService


logger = logging.getLogger(__name__)


class EmployeeHistoryReportView(APIView):
    """
    API View for generating employee history reports based on sales performance.
    
    This view handles the generation of reports showing employee sales performance
    including frames, lenses, factory orders, and normal orders within a date range.
    """
    
    def get(self, request):
        import time
        print("[DEBUG] EmployeeHistoryReportView.get called")
        t0 = time.time()
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
            print(f"[DEBUG] Step 1: Extracting query parameters (t={time.time()-t0:.3f}s)")
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            employee_code = request.GET.get('employee_code')
            branch_id = request.GET.get('branch_id')
            include_summary = request.GET.get('include_summary', 'false').lower() == 'true'
            print(f"[DEBUG] start_date={start_date}, end_date={end_date}, employee_code={employee_code}, branch_id={branch_id}, include_summary={include_summary}")

            # Validate required parameters
            print(f"[DEBUG] Step 2: Validating required parameters (t={time.time()-t0:.3f}s)")
            if not all([start_date, end_date]):
                print("[DEBUG] Missing required parameters")
                return Response({
                    'error': 'Missing required parameters',
                    'details': 'start_date and end_date are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Convert dates to timezone-aware datetimes
            print(f"[DEBUG] Step 3: Converting dates to timezone-aware datetimes (t={time.time()-t0:.3f}s)")
            start_dt, end_dt = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
            print(f"[DEBUG] start_dt={start_dt}, end_dt={end_dt}")
            if not start_dt or not end_dt:
                print("[DEBUG] Invalid date format")
                return Response({
                    'error': 'Invalid date format',
                    'details': 'Invalid or missing start_date/end_date. Use YYYY-MM-DD format.'
                }, status=status.HTTP_400_BAD_REQUEST)
            if start_dt > end_dt:
                print("[DEBUG] Invalid date range: start_dt > end_dt")
                return Response({
                    'error': 'Invalid date range',
                    'details': 'start_date cannot be after end_date.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate branch_id if provided
            print(f"[DEBUG] Step 4: Validating branch_id (t={time.time()-t0:.3f}s)")
            branch_id_int = None
            if branch_id:
                try:
                    branch_id_int = int(branch_id)
                    if branch_id_int <= 0:
                        print("[DEBUG] branch_id_int <= 0")
                        raise ValueError("Branch ID must be a positive integer")
                except ValueError:
                    print("[DEBUG] Invalid branch_id")
                    return Response({
                        'error': 'Invalid branch_id',
                        'details': 'Branch ID must be a positive integer'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Generate report
            print(f"[DEBUG] Step 5: Generating employee report (t={time.time()-t0:.3f}s)")
            employees_data = EmployeeReportService.get_employee_history_report(
                start_dt, end_dt, employee_code, branch_id_int
            )
            print(f"[DEBUG] employees_data count: {len(employees_data)} (t={time.time()-t0:.3f}s)")

            # Prepare response
            print(f"[DEBUG] Step 6: Preparing response (t={time.time()-t0:.3f}s)")
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
                print(f"[DEBUG] Step 7: Generating summary (t={time.time()-t0:.3f}s)")
                summary_data = EmployeeReportService.get_report_summary(
                    start_dt, end_dt, branch_id_int
                )
                response_data['data']['summary'] = summary_data

            print(f"[DEBUG] Step 8: Returning response (t={time.time()-t0:.3f}s)")
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"[DEBUG] Exception occurred: {str(e)} (t={time.time()-t0:.3f}s)")
            logger.error(f"Error generating employee history report: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'details': 'An error occurred while generating the report'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)