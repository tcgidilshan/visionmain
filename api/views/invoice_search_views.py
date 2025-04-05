from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from ..services.Invoice_service import InvoiceService
from ..serializers import InvoiceSerializer,InvoiceSearchSerializer
from rest_framework.pagination import PageNumberPagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow client to override
    max_page_size = 100  # Maximum limit

class FactoryInvoiceSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    def get(self, request):
        invoice_number = request.query_params.get('invoice_number')
        mobile = request.query_params.get('mobile')
        nic = request.query_params.get('nic')
        progress_status = request.query_params.get('progress_status')
        branch_id = request.query_params.get('branch_id')

        if not any([invoice_number, mobile, nic,progress_status,branch_id]):
            return Response(
                {"error": "Please provide at least one search parameter: invoice_number, mobile, or nic."},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = InvoiceService.search_factory_invoices(
            user=request.user,
            invoice_number=invoice_number,
            mobile=mobile,
            nic=nic,
            progress_status=progress_status,
            branch_id=branch_id
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(invoices, request)
        if page is not None:
            serializer = InvoiceSearchSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        #InvoiceSearchSerializer provide only nesasry info for the checkin module
        serializer = InvoiceSearchSerializer(invoices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
