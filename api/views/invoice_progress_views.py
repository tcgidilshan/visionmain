from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from api.models import Invoice,Order,OrderItemWhatsAppLog
from api.serializers import InvoiceSerializer,BulkWhatsAppLogCreateSerializer
from django.utils import timezone
from django.db import transaction
from api.models import OrderProgress

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
                from api.serializers import OrderSerializer  # Import as needed
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

    def post(self, request, *args, **kwargs):
        order_ids = request.data.get("order_ids", [])
        progress_status = request.data.get("progress_status", None)

        if not order_ids or not progress_status:
            return Response({"detail": "order_ids and progress_status required."}, status=400)

        results = []
        with transaction.atomic():
            # Lock the orders to prevent concurrent issues
            orders = Order.objects.select_for_update().filter(id__in=order_ids, is_deleted=False)
            for order in orders:
                # Fetch the latest OrderProgress record for this order
                last_progress = (
                    OrderProgress.objects
                    .filter(order=order)
                    .order_by('-changed_at')
                    .first()
                )
                if last_progress and last_progress.progress_status == progress_status:
                    results.append({"order_id": order.id, "status": "already_set"})
                    continue

                # Create a new progress record
                OrderProgress.objects.create(
                    order=order,
                    progress_status=progress_status,
                    changed_at=timezone.now()
                )
                results.append({"order_id": order.id, "status": "created"})

        return Response({"results": results}, status=200)

class BulkOrderWhatsAppLogView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = BulkWhatsAppLogCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_ids = serializer.validated_data['order_ids']
        urgent_order_ids = serializer.validated_data.get('urgent_order_ids', [])

        logs_created = []
        already_exists = []
        now = timezone.now()

        for oid in order_ids:
            # Get the latest WhatsApp log for this order
            latest_log = OrderItemWhatsAppLog.objects.filter(
                order_id=oid
            ).order_by('-created_at').first()
            
            # Only prevent update if latest status is 'sent'
            if latest_log and latest_log.status == 'sent':
                already_exists.append(oid)
                continue

            # Create new log with 'sent' status
            OrderItemWhatsAppLog.objects.create(
                order_id=oid,
                status='sent',
                created_at=now
            )
            logs_created.append(oid)

        # Mark urgent, only for non-deleted, valid Orders
        if urgent_order_ids:
            #TODO Only update if order is not soft deleted
            Order.objects.filter(id__in=urgent_order_ids, is_deleted=False).update(urgent=True)

        return Response({
            "logs_created": logs_created,
            "already_exists_today": already_exists,
            "marked_urgent": urgent_order_ids
        }, status=status.HTTP_201_CREATED)
