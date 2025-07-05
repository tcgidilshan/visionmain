from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, InvalidOperation
import logging
from django.utils import timezone

from ..services.customer_report_service import CustomerReportService


logger = logging.getLogger(__name__)


class BestCustomersReportView(APIView):
    """
    API View for generating best customers report based on factory orders.
    
    This view handles the generation of reports showing customers with the highest
    spending on factory orders within a specified date range and budget criteria.
    """
    
    def get(self, request):
        """
        GET endpoint to retrieve best customers report.
        
        Query Parameters:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            min_budget (float): Minimum budget amount to filter customers
            include_summary (bool): Whether to include summary statistics
            
        Returns:
            JSON response with customer report data
        """
        
        try:
            # Extract query parameters
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            min_budget = request.GET.get('min_budget')
            include_summary = request.GET.get('include_summary', 'false').lower() == 'true'
            
            # Validate required parameters
            if not all([start_date, end_date, min_budget]):
                return Response({
                    'error': 'Missing required parameters',
                    'details': 'start_date, end_date, and min_budget are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate and convert dates
            try:
                start_dt, end_dt = CustomerReportService.validate_date_range(
                    start_date, end_date
                )
            except ValueError as e:
                return Response({
                    'error': 'Invalid date format',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate budget amount
            try:
                min_budget_decimal = Decimal(min_budget)
                if min_budget_decimal < 0:
                    raise ValueError("Budget amount cannot be negative")
            except (InvalidOperation, ValueError) as e:
                return Response({
                    'error': 'Invalid budget amount',
                    'details': 'Budget must be a valid positive number'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate report
            customers_data = CustomerReportService.get_best_customers_report(
                start_dt, end_dt, float(min_budget_decimal)
            )
            
            # Prepare response
            response_data = {
                'success': True,
                'data': {
                    'customers': customers_data,
                    'criteria': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'min_budget': float(min_budget_decimal)
                    },
                    'count': len(customers_data),
                    'generated_at': timezone.now().isoformat()
                }
            }
            
            # Include summary if requested
            if include_summary:
                summary_data = CustomerReportService.get_report_summary(
                    start_dt, end_dt, float(min_budget_decimal)
                )
                response_data['data']['summary'] = summary_data
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating best customers report: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'details': 'An error occurred while generating the report'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)