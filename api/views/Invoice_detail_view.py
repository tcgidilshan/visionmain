from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import Invoice
from ..serializers import InvoiceSerializer

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
                invoice = Invoice.objects.get(order_id=order_id)
                serializer = self.get_serializer(invoice)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Invoice.DoesNotExist:
                return Response({"error": "No invoice found for this order."}, status=status.HTTP_404_NOT_FOUND)

        return super().get(request, *args, **kwargs)  # If no order_id, fallback to ID-based retrieval
