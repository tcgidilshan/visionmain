from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from ..models import Order, OrderItem, HearingOrderItemService
from ..serializers import HearingOrderItemServiceSerializer

class HearingOrderServiceView(APIView):
    def get(self, request):
        order_id = request.query_params.get('order_id')
        
        if not order_id:
            return Response(
                {"error": "order_id parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get all service records for the order, ordered by creation date (newest first)
            services = HearingOrderItemService.objects.filter(
                order_id=order_id
            ).order_by('-created_at')
            
            if not services.exists():
                return Response(
                    {"message": "No service records found for this order"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Serialize the data
            serializer = HearingOrderItemServiceSerializer(services, many=True)
            
            # Get the order item details if available
            order_item = OrderItem.objects.filter(
                order_id=order_id,
                hearing_item__isnull=False
            ).select_related('hearing_item').first()
            
            response_data = {
                "order_id": order_id,
                "total_services": services.count(),
                "services": serializer.data,
                "order_item": {
                    "id": order_item.id if order_item else None,
                    "item_name": order_item.hearing_item.name if (order_item and order_item.hearing_item) else None,
                    "next_service_date": order_item.next_service_date.isoformat() if (order_item and order_item.next_service_date) else None
                } if order_item else None
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
