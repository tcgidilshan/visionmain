from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.services.invoice_report_service import InvoiceReportService
from api.services.time_zone_convert_service import TimezoneConverterService


class InvoiceReportView(APIView):
    """
    API View to fetch invoice reports by payment date and branch.
    """

    def get(self, request, *args, **kwargs):
        
        payment_date = request.query_params.get("payment_date")
        branch_id = request.query_params.get("branch_id")
                
        if not payment_date or not branch_id:
                     
            return Response({"error": "payment_date and branch_id are required."}, status=400)

        try:
            
            report_data = InvoiceReportService.get_invoice_report_by_payment_date(payment_date, branch_id)
                                                                                 
            return Response(report_data, status=status.HTTP_200_OK)

        except ValueError as e:
                       
            return Response({"error": str(e)}, status=400)

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            error_msg = f"DEBUG: Unexpected error in InvoiceReportView - {str(e)}\n{error_trace}"
           
            return Response({"error": f"Something went wrong: {str(e)}"}, status=500)


class FactoryOrderReportView(APIView):
    """
    API endpoint to generate factory order reports.
    """
    
    def get(self, request, format=None):
        # Get query parameters with defaults
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        filter_type = request.query_params.get('filter_type', 'payment_date')  # Default to payment_date
        
        # Validate required parameters
        if not all([start_date, end_date, branch_id]):
            return Response(
                {"error": "start_date, end_date, and branch_id are required parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate filter_type
        if filter_type not in ['payment_date', 'invoice_date', 'all']:
            return Response(
                {"error": "filter_type must be 'payment_date', 'invoice_date', or 'all'"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert branch_id to integer
            branch_id = int(branch_id)
            
            # Generate the report
            report_data = InvoiceReportService.get_factory_order_report(
                start_date_str=start_date,
                end_date_str=end_date,
                branch_id=branch_id,
                filter_type=filter_type
            )
            
            return Response({
                "success": True,
                "data": report_data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class NormalOrderReportView(APIView):
    """
    API endpoint to generate normal order reports.
    """
    
    def get(self, request, format=None):
        # Get query parameters with defaults
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        filter_type = request.query_params.get('filter_type', 'payment_date')  # Default to payment_date

        
        # Validate required parameters
        if not all([start_date, end_date, branch_id]):
            return Response(
                {"error": "start_date, end_date, and branch_id are required parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
         
        # Validate filter_type
        if filter_type not in ['payment_date', 'invoice_date', 'all']:
            return Response(
                {"error": "filter_type must be 'payment_date', 'invoice_date', or 'all'"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert branch_id to integer
            branch_id = int(branch_id)
            
            # Generate the report
            report_data = InvoiceReportService.get_normal_order_report(
                start_date_str=start_date,
                end_date_str=end_date,
                branch_id=branch_id,
                filter_type=filter_type
            )
            
            return Response({
                "success": True,
                "data": report_data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class ChannelOrderReportView(APIView):
    """
    API endpoint to generate channel order reports.
    """
    
    def get(self, request, format=None):
        # Get query parameters with defaults
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        
        # Validate required parameters
        if not all([start_date, end_date, branch_id]):
            return Response(
                {"error": "start_date, end_date, and branch_id are required parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert branch_id to integer
            branch_id = int(branch_id)
            
            # Generate the report
            report_data = InvoiceReportService.get_channel_order_report(
                start_date_str=start_date,
                end_date_str=end_date,
                branch_id=branch_id
            )
            
            return Response({
                "success": True,
                "data": report_data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SolderingOrderReportView(APIView):
    """
    API endpoint to generate soldering order reports.
    """
    def get(self, request, format=None):
        # Get query parameters with defaults
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        
        # Validate required parameters
        if not all([start_date, end_date, branch_id]):
            return Response(
                {"error": "start_date, end_date, and branch_id are required parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert branch_id to integer
            branch_id = int(branch_id)
            
            # Generate the report
            report_data = InvoiceReportService.get_soldering_order_report(
                start_date_str=start_date,
                end_date_str=end_date,
                branch_id=branch_id
            )
            
            return Response({
                "success": True,
                "data": report_data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class HearingOrderReportView(APIView):
    """
    API endpoint to generate hearing order reports.
    """
    
    def get(self, request, format=None):
        # Get query parameters with defaults
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        filter_type = request.query_params.get('filter_type', 'payment_date')  # Default to payment_date
        
        # Validate required parameters
        if not all([start_date, end_date, branch_id]):
            return Response(
                {"error": "start_date, end_date, and branch_id are required parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate filter_type
        if filter_type not in ['payment_date', 'invoice_date', 'all']:
            return Response(
                {"error": "filter_type must be 'payment_date', 'invoice_date', or 'all'"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert branch_id to integer
            branch_id = int(branch_id)
            
            # Generate the report
            report_data = InvoiceReportService.get_hearing_order_report(
                start_date_str=start_date,
                end_date_str=end_date,
                branch_id=branch_id,
                filter_type=filter_type
            )
            
            return Response({
                "success": True,
                "data": report_data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
