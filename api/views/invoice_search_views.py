from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from ..services.Invoice_service import InvoiceService
from ..serializers import InvoiceSerializer

class FactoryInvoiceSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invoice_number = request.query_params.get('invoice_number')
        mobile = request.query_params.get('mobile')
        nic = request.query_params.get('nic')

        if not any([invoice_number, mobile, nic]):
            return Response(
                {"error": "Please provide at least one search parameter: invoice_number, mobile, or nic."},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = InvoiceService.search_factory_invoices(
            user=request.user,
            invoice_number=invoice_number,
            mobile=mobile,
            nic=nic
        )

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
