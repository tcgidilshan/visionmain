from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, InvalidOperation
import logging
from django.utils import timezone

from ..services.customer_report_service import CustomerReportService
from ..services.customer_report_service import CustomerLocationReportService


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
            include_invoices (bool): Whether to include detailed invoice information
            
        Returns:
            JSON response with customer report data including invoice details
        """
        
        try:
            # Extract query parameters
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            min_budget = request.GET.get('min_budget')
            include_summary = request.GET.get('include_summary', 'false').lower() == 'true'
            include_invoices = request.GET.get('include_invoices', 'true').lower() == 'true'
            
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
            
            # Remove invoice details if not requested
            if not include_invoices:
                for customer in customers_data:
                    customer.pop('invoices', None)
                    customer.pop('invoice_count', None)
            
            # Prepare response
            response_data = {
                'success': True,
                'data': {
                    'customers': customers_data,
                    'criteria': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'min_budget': float(min_budget_decimal),
                        'include_invoices': include_invoices
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
            
class CustomerLocationTableView(APIView):
    """
    Simple API View for Customer Location Table data.
    Returns only the essential fields needed for table display.
    """
    
    def get(self, request):
        """
        Get customer table data by location (district and town).
        
        Query Parameters:
            - district (required): District name
            - town (required): Town name  
            - branch_id (optional): Branch ID to filter by specific branch
        
        Returns:
            JSON response with customer table data:
            - Invoice Number
            - Customer Name  
            - Mobile Number
            - Address
            - Date (of transaction or visit)
            - Age (of the customer, if available)
        """
        try:
            # Get query parameters
            district = request.query_params.get('district')
            town = request.query_params.get('town')
            branch_id = request.query_params.get('branch_id')
            
            # Validate required parameters
            if not district:
                return Response(
                    {'error': 'District parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not town:
                return Response(
                    {'error': 'Town parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert branch_id to int if provided
            if branch_id:
                try:
                    branch_id = int(branch_id)
                except ValueError:
                    return Response(
                        {'error': 'Invalid branch_id format'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get customer table data
            customers_data = CustomerLocationReportService.get_customers_table_data(
                district=district,
                town=town,
                branch_id=branch_id
            )
            
            response_data = {
                'success': True,
                'message': f'Found {len(customers_data)} customers in {town}, {district}',
                'data': customers_data
            }
            
            logger.info(f"Customer location table data generated: {district}, {town} - {len(customers_data)} records")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in CustomerLocationTableView.get: {str(e)}")
            return Response(
                {'error': 'Internal server error occurred', 'detail': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomerLocationOptionsView(APIView):
    """
    API View to get available location options for the map interface.
    Returns all available districts and towns from customer addresses.
    """
    
    def get(self, request):
        """
        Get all available districts and towns from customer addresses.
        
        Returns:
            JSON response with available locations for map selection
        """
        try:
            location_data = CustomerLocationReportService.get_available_locations()
            
            # Transform data for easier frontend consumption
            locations = []
            for district, towns in location_data.items():
                locations.append({
                    'district': district,
                    'towns': towns,
                    'town_count': len(towns)
                })
            
            response_data = {
                'success': True,
                'message': f'Found {len(location_data)} districts with towns',
                'data': {
                    'locations': locations,
                    'total_districts': len(location_data),
                    'total_unique_locations': sum(len(towns) for towns in location_data.values())
                }
            }
            
            logger.info(f"Location options retrieved: {len(location_data)} districts")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in CustomerLocationOptionsView.get: {str(e)}")
            return Response(
                {'error': 'Internal server error occurred', 'detail': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomerLocationStatisticsView(APIView):
    """
    API View to get statistics for customers in a specific location.
    Provides summary data for dashboard and reporting purposes.
    """
    
    def get(self, request):
        """
        Get customer statistics for a specific location.
        
        Query Parameters:
            - district (required): District name
            - town (required): Town name
            - branch_id (optional): Branch ID to filter by specific branch
        
        Returns:
            JSON response with location statistics
        """
        try:
            # Get query parameters
            district = request.query_params.get('district')
            town = request.query_params.get('town')
            branch_id = request.query_params.get('branch_id')
            
            # Validate required parameters
            if not district:
                return Response(
                    {'error': 'District parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not town:
                return Response(
                    {'error': 'Town parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert branch_id to int if provided
            if branch_id:
                try:
                    branch_id = int(branch_id)
                except ValueError:
                    return Response(
                        {'error': 'Invalid branch_id format'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get statistics
            stats = CustomerLocationReportService.get_customer_statistics_by_location(
                district=district,
                town=town,
                branch_id=branch_id
            )
            
            response_data = {
                'success': True,
                'message': f'Statistics retrieved for {town}, {district}',
                'data': {
                    'statistics': stats,
                    'summary': {
                        'location': f"{town}, {district}",
                        'performance_metrics': {
                            'average_order_value': round(stats['total_revenue'] / stats['total_orders'], 2) if stats['total_orders'] > 0 else 0,
                            'order_rate': round((stats['total_orders'] / stats['total_customers']) * 100, 2) if stats['total_customers'] > 0 else 0
                        }
                    }
                }
            }
            
            logger.info(f"Location statistics retrieved: {district}, {town}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in CustomerLocationStatisticsView.get: {str(e)}")
            return Response(
                {'error': 'Internal server error occurred', 'detail': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


