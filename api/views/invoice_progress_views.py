from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from api.models import Invoice
from api.serializers import InvoiceSerializer

class InvoiceProgressUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        try:
            invoice = Invoice.objects.select_related('order').get(pk=pk)

            if invoice.invoice_type != 'factory':
                return Response({"error": "This action is only allowed for factory invoices."},
                                status=status.HTTP_400_BAD_REQUEST)

            order = invoice.order

            allowed_fields = {'progress_status', 'lens_arrival_status', 'whatsapp_sent'}
            data = {k: v for k, v in request.data.items() if k in allowed_fields}

            # Split update targets
            invoice_fields = {'lens_arrival_status', 'whatsapp_sent'}
            order_fields = {'progress_status'}

            invoice_data = {k: v for k, v in data.items() if k in invoice_fields}
            order_data = {k: v for k, v in data.items() if k in order_fields}

            # Update Invoice
            if invoice_data:
                invoice_serializer = InvoiceSerializer(invoice, data=invoice_data, partial=True)
                invoice_serializer.is_valid(raise_exception=True)
                invoice_serializer.save()

            # Update Order
            if order_data:
                from api.serializers import OrderSerializer  # 🔁 Import as needed
                order_serializer = OrderSerializer(order, data=order_data, partial=True)
                order_serializer.is_valid(raise_exception=True)
                order_serializer.save()

            return Response({
                "message": "Status updated successfully.",
                "invoice": InvoiceSerializer(invoice).data
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

            invoices = Invoice.objects.select_related('order').filter(
                id__in=invoice_ids, invoice_type='factory'
            )
            found_ids = set(invoices.values_list('id', flat=True))
            missing_ids = set(invoice_ids) - found_ids

            if missing_ids:
                return Response(
                    {"error": f"Invoices not found or not factory type: {list(missing_ids)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Separate invoice/order fields
            allowed_invoice_fields = {'lens_arrival_status', 'whatsapp_sent'}
            allowed_order_fields = {'progress_status'}

            invoice_data = {k: v for k, v in request.data.items() if k in allowed_invoice_fields}
            order_data = {k: v for k, v in request.data.items() if k in allowed_order_fields}

            if not (invoice_data or order_data):
                return Response({"error": "No valid fields to update."},
                                status=status.HTTP_400_BAD_REQUEST)

            updated_invoices = []
            updated_orders = []

            for invoice in invoices:
                # Update invoice fields
                for field, value in invoice_data.items():
                    setattr(invoice, field, value)
                updated_invoices.append(invoice)

                # Update order fields
                if invoice.order and order_data:
                    for field, value in order_data.items():
                        setattr(invoice.order, field, value)
                    updated_orders.append(invoice.order)

            # Bulk update both models
            if updated_invoices:
                Invoice.objects.bulk_update(updated_invoices, fields=invoice_data.keys())
            if updated_orders:
                from api.models import Order  # in case not imported
                Order.objects.bulk_update(updated_orders, fields=order_data.keys())

            return Response({
                "message": f"Updated {len(updated_invoices)} invoices.",
                "updated_ids": list(found_ids)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
