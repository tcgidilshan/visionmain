from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import Order, OrderItem, OrderPayment, LensStock, LensCleanerStock, FrameStock
from ..serializers import OrderSerializer, OrderItemSerializer, OrderPaymentSerializer

class OrderCreateView(APIView):

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Create an order with stock validation, order creation, and stock adjustment.
        """
        try:
            # Step 1: Start transaction
            with transaction.atomic():
                # Step 2: Validate Stocks
                order_items_data = request.data.get('order_items', [])
                if not order_items_data:
                    raise ValueError("Order items are required.")

                stock_updates = []  # Prepare stock updates
                for item_data in order_items_data:
                    if item_data.get('lens'):
                        stock = LensStock.objects.select_for_update().get(lens__id=item_data['lens'])
                        if stock.qty < item_data['quantity']:
                            raise ValueError(f"Insufficient stock for Lens ID {item_data['lens']}.")
                        stock_updates.append(('lens', stock, item_data['quantity']))
                    elif item_data.get('lens_cleaner'):
                        stock = LensCleanerStock.objects.select_for_update().get(lens_cleaner_id=item_data['lens_cleaner'])
                        if stock.qty < item_data['quantity']:
                            raise ValueError(f"Insufficient stock for Lens Cleaner ID {item_data['lens_cleaner']}.")
                        stock_updates.append(('lens_cleaner', stock, item_data['quantity']))
                    elif item_data.get('frame'):
                        stock = FrameStock.objects.select_for_update().get(frame_id=item_data['frame'])
                        if stock.qty < item_data['quantity']:
                            raise ValueError(f"Insufficient stock for Frame ID {item_data['frame']}.")
                        stock_updates.append(('frame', stock, item_data['quantity']))

                # Step 3: Create Order
                order_data = request.data.get('order')
                order_serializer = OrderSerializer(data=order_data)
                order_serializer.is_valid(raise_exception=True)
                order = order_serializer.save()

                # Step 4: Create Order Items
                for item_data in order_items_data:
                    item_data['order'] = order.id
                    order_item_serializer = OrderItemSerializer(data=item_data)
                    order_item_serializer.is_valid(raise_exception=True)
                    order_item_serializer.save()

                # Step 5: Create Order Payment
                payment_data = request.data.get('order_payment')
                if not payment_data:
                    raise ValueError("Order payment is required.")
                payment_data['order'] = order.id
                order_payment_serializer = OrderPaymentSerializer(data=payment_data)
                order_payment_serializer.is_valid(raise_exception=True)
                order_payment_serializer.save()

                # Step 6: Adjust Stocks
                for stock_type, stock, quantity in stock_updates:
                    stock.qty -= quantity
                    stock.save()

                # Return successful response
                return Response({
                    "order": order_serializer.data,
                    "order_items": [item for item in order_items_data],
                    "order_payment": payment_data
                }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
