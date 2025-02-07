from rest_framework.generics import RetrieveAPIView
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
