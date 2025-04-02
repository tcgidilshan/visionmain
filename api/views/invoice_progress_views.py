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
        
class BulkInvoiceProgressUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        try:
            invoice_ids = request.data.get('ids', [])
            if not invoice_ids:
                return Response({"error": "No invoice IDs provided."}, 
                                status=status.HTTP_400_BAD_REQUEST)

            # Fetch invoices that are of type 'factory' and match the provided IDs
            invoices = Invoice.objects.filter(id__in=invoice_ids, invoice_type='factory')
            found_ids = set(invoices.values_list('id', flat=True))
            missing_ids = set(invoice_ids) - found_ids

            if missing_ids:
                return Response(
                    {"error": f"Invoices not found or not factory type: {list(missing_ids)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract allowed fields from request data
            allowed_fields = {'progress_status', 'lens_arrival_status', 'whatsapp_sent'}
            data_to_update = {k: v for k, v in request.data.items() if k in allowed_fields}

            if not data_to_update:
                return Response({"error": "No valid fields to update."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Validate data for each invoice and prepare for bulk update
            updated_invoices = []
            for invoice in invoices:
                serializer = InvoiceSerializer(invoice, data=data_to_update, partial=True)
                serializer.is_valid(raise_exception=True)  # Validate each invoice
                # Manually update the instance
                for field, value in data_to_update.items():
                    setattr(invoice, field, value)
                updated_invoices.append(invoice)

            # Perform bulk update
            Invoice.objects.bulk_update(updated_invoices, fields=data_to_update.keys())

            # Serialize the response
            serializer = InvoiceSerializer(updated_invoices, many=True)
            return Response({
                "message": f"Successfully updated {len(updated_invoices)} invoices.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Invoice.DoesNotExist:
            return Response({"error": "One or more invoices not found."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)