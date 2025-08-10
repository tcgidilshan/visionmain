from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from ..models import OrderItem

class OrderItemUpdateView(APIView):
    def put(self, request):
        try:
            order_item_id = request.data.get('order_item_id')
            if not order_item_id:
                return Response(
                    {"error": "order_item_id is required in request body"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Lock the row for the duration of the transaction
                order_item = OrderItem.objects.select_for_update().get(id=order_item_id)
                order_item.last_reminder_at = timezone.now()
                order_item.save(update_fields=['last_reminder_at'])
                
                return Response({
                    "id": order_item.id,
                    "last_reminder_at": order_item.last_reminder_at
                })
                
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Order item not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )