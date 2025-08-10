from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from ..models import Order, OrderItem, HearingOrderItemService
from ..serializers import HearingOrderItemServiceSerializer

class HearingOrderServiceView(APIView):
    def post(self, request):
        try:
            required_fields = [
                'order_id',
                'last_service_date',
                'scheduled_service_date',
                'price',
                'next_service_date'
            ]
            
            # Check for missing required fields
            missing_fields = [field for field in required_fields if field not in request.data]
            if missing_fields:
                return Response(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            order_id = request.data['order_id']
            
            with transaction.atomic():
                # 1. Create HearingOrderItemService record
                service_data = {
                    'order': order_id,  
                    'last_service_date': request.data['last_service_date'],
                    'scheduled_service_date': request.data['scheduled_service_date'],
                    'price': request.data['price']
                }
                
                serializer = HearingOrderItemServiceSerializer(data=service_data)
                if not serializer.is_valid():
                    return Response(
                        {"error": "Invalid service data", "details": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                service = serializer.save()
                
                # 2. Update OrderItem's next_service_date
                order_item = OrderItem.objects.filter(
                    order_id=order_id,
                    hearing_item__isnull=False
                ).first()
                
                if order_item:
                    order_item.next_service_date = request.data['next_service_date']
                    order_item.save(update_fields=['next_service_date'])
                
                # Prepare response data
                response_data = {
                    "service_id": service.id,
                    "order_id": order_id,
                    "order_item_updated": order_item is not None,
                    "next_service_date": request.data['next_service_date'],
                    "service_data": HearingOrderItemServiceSerializer(service).data,
                    "message": "Service record created and order item updated successfully"
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )