from ..models import Order
from ..serializers import OrderSerializer, OrderItemSerializer

class OrderService:
    """
    Handles order and order item creation.
    """

    @staticmethod
    def create_order(order_data, order_items_data):
        """
        Creates an order and its related order items.
        Raises validation errors if any issues occur.
        Returns the created order instance.
        """
        # Step 1: Create Order
        order_serializer = OrderSerializer(data=order_data)
        order_serializer.is_valid(raise_exception=True)
        order = order_serializer.save()

        # Step 2: Create Order Items
        order_items = []
        for item_data in order_items_data:
            item_data['order'] = order.id  # Attach the created order
            order_item_serializer = OrderItemSerializer(data=item_data)
            order_item_serializer.is_valid(raise_exception=True)
            order_items.append(order_item_serializer.save())  # Save and store items

        return order  # Return the created order instance
