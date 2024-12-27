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

                # Step 5: Create Order Payments
                order_payments_data = request.data.get('order_payments')
                if not order_payments_data or not isinstance(order_payments_data, list):
                    raise ValueError("At least one order payment is required.")

                total_payment = 0

                for payment_data in order_payments_data:
                    # Attach the order ID
                    payment_data['order'] = order.id

                    # Determine if this payment is partial
                    if total_payment + payment_data['amount'] < order.total_price:
                        payment_data['is_partial'] = True
                    else:
                        payment_data['is_partial'] = False

                    # Validate and save each payment
                    order_payment_serializer = OrderPaymentSerializer(data=payment_data)
                    order_payment_serializer.is_valid(raise_exception=True)
                    payment_instance = order_payment_serializer.save()  # Save and get the instance

                    # Track the total payment
                    total_payment += payment_data['amount']

                    # Check if this is the final payment
                    if total_payment == order.total_price:
                        payment_instance.is_final_payment = True
                    else:
                        payment_instance.is_final_payment = False

                    # Save the final changes to the instance
                    payment_instance.save()

                # Ensure total payment does not exceed the order total price
                if total_payment > order.total_price:
                    raise ValueError("Total payments exceed the order total price.")

                # Refresh the order instance to include related order_payments
                order.refresh_from_db()


                # Ensure total payment does not exceed the order total price
                if total_payment > order.total_price:
                    raise ValueError("Total payments exceed the order total price.")

                # Step 6: Adjust Stocks
                for stock_type, stock, quantity in stock_updates:
                    stock.qty -= quantity
                    stock.save()

                # Return successful response
                response_serializer = OrderSerializer(order)
                return Response(response_serializer.data, status=201)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
