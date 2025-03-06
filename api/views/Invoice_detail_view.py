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
        """
        Retrieve invoice details based on invoice ID or order_id.
        """
        order_id = request.query_params.get("order_id")  # ✅ Get order_id from query params

        if order_id:
            try:
                invoice_data = InvoiceService.get_invoice_by_order_id(order_id)  # ✅ Get serialized invoice
                return Response(invoice_data, status=status.HTTP_200_OK)
            except NotFound as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        return super().get(request, *args, **kwargs)  # ✅ Fallback to ID-based retrieval
