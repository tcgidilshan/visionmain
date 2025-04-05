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
