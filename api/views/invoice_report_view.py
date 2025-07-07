from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.services.invoice_report_service import InvoiceReportService


class InvoiceReportView(APIView):
    """
    API View to fetch invoice reports by payment date and branch.
    """

    def get(self, request, *args, **kwargs):
        print("\n=== DEBUG: InvoiceReportView.get() called ===")
        payment_date = request.query_params.get("payment_date")
        branch_id = request.query_params.get("branch_id")
        
        print(f"DEBUG: Request query params - payment_date: {payment_date}, branch_id: {branch_id}")

        if not payment_date or not branch_id:
            error_msg = f"DEBUG: Missing required parameters - payment_date: {payment_date}, branch_id: {branch_id}"
            print(error_msg)
            return Response({"error": "payment_date and branch_id are required."}, status=400)

        try:
            print(f"DEBUG: Calling InvoiceReportService.get_invoice_report_by_payment_date with payment_date={payment_date}, branch_id={branch_id}")
            report_data = InvoiceReportService.get_invoice_report_by_payment_date(payment_date, branch_id)
            
            # Enhanced type checking and logging
            data_type = type(report_data).__name__
            print(f"DEBUG: Report data type: {data_type}")
            
            if isinstance(report_data, dict):
                print(f"DEBUG: Report data keys: {list(report_data.keys())}")
                print(f"DEBUG: Report data values: {list(report_data.values())}")
            elif hasattr(report_data, '__iter__') and not isinstance(report_data, str):
                print(f"DEBUG: Report data is iterable with length: {len(list(report_data)) if hasattr(report_data, '__len__') else 'unknown'}")
                print(f"DEBUG: First few items: {list(report_data)[:3] if hasattr(report_data, '__getitem__') else 'Not indexable'}")
            
            print(f"DEBUG: Full report data: {report_data}")
            
            return Response(report_data, status=status.HTTP_200_OK)

        except ValueError as e:
            error_msg = f"DEBUG: ValueError in InvoiceReportView - {str(e)}"
            print(error_msg)
            return Response({"error": str(e)}, status=400)

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            error_msg = f"DEBUG: Unexpected error in InvoiceReportView - {str(e)}\n{error_trace}"
            print(error_msg)
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
            report_data = InvoiceReportService.get_factory_order_report(
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
            
class NormalOrderReportView(APIView):
    """
    API endpoint to generate normal order reports.
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
            report_data = InvoiceReportService.get_normal_order_report(
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