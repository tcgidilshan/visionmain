from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from api.models import Invoice,Order,OrderItem
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
        
class BulkUpdateOrderProgressStatus(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        order_ids = request.data.get('order_ids')
        new_status = request.data.get('progress_status')

        if not order_ids or not isinstance(order_ids, list):
            return Response({'error': 'Invalid or missing "order_ids". Must be a list of IDs.'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = dict(Order._meta.get_field('progress_status').choices).keys()
        if new_status not in valid_statuses:
            return Response({'error': f'Invalid progress_status. Valid options: {list(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Update orders
        updated_count = Order.objects.filter(id__in=order_ids).update(progress_status=new_status)

        return Response({
            'message': f'{updated_count} order(s) updated successfully.',
            'progress_status': new_status,
            'order_ids': order_ids
        }, status=status.HTTP_200_OK)
class BulkUpdateOrderWhatAppMsgSent(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def patch(self, request):
        order_ids = request.data.get('order_ids', [])
        whatsapp_sent = request.data.get('whatsapp_sent')

        if not order_ids or whatsapp_sent not in ['sent', 'not_sent']:
            return Response(
                {"error": "Invalid input. Provide 'order_ids' and a valid 'whatsapp_sent' value ('sent' or 'not_sent')."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter and bulk update
        updated_count = OrderItem.objects.filter(order_id__in=order_ids).update(whatsapp_sent=whatsapp_sent)

        return Response(
            {"message": f"Updated {updated_count} order items successfully."},
            status=status.HTTP_200_OK
        )