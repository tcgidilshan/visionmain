from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from api.models import Invoice
from api.serializers import InvoiceSerializer

class InvoiceProgressUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(pk=pk)

            if invoice.invoice_type != 'factory':
                return Response({"error": "This action is only allowed for factory invoices."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Only allow updating progress-related fields
            allowed_fields = {'progress_status', 'lens_arrival_status', 'whatsapp_sent'}
            data = {k: v for k, v in request.data.items() if k in allowed_fields}

            serializer = InvoiceSerializer(invoice, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({
                "message": "Invoice status updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
