from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.services.invoice_report_service import InvoiceReportService


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