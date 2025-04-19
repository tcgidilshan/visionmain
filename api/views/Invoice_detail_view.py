from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import Invoice
from ..serializers import InvoiceSerializer
from ..services.Invoice_service import InvoiceService
from rest_framework.exceptions import NotFound
class InvoiceDetailView(RetrieveAPIView):
    """
    Retrieve a single invoice with full details.
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        invoice_type = request.query_params.get("invoice_type")
        invoice_number = request.query_params.get("invoice_number")

        if invoice_type and invoice_number:
            try:
                invoice_data = InvoiceService.get_invoice_by_invoice_number(invoice_type, invoice_number)
                return Response(invoice_data, status=status.HTTP_200_OK)
            except NotFound as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {"error": "Both 'invoice_type' and 'invoice_number' are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
