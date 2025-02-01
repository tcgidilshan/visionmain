from django.db import transaction
from ..models import LensStock, LensCleanerStock, FrameStock

class StockValidationService:
    """
    Service to handle stock validation for orders.
    """

    @staticmethod
    def validate_stocks(order_items_data):
        """
        Validates stock availability for given order items.
        Raises ValueError if stock is insufficient.
        Returns a list of stock updates.
        """
        if not order_items_data:
            raise ValueError("Order items are required.")

        stock_updates = []  # List to track stock changes

        with transaction.atomic():
            for item_data in order_items_data:
                if item_data.get('lens'):
                    stock = LensStock.objects.select_for_update().filter(lens__id=item_data['lens']).first()
                    if not stock or stock.qty < item_data['quantity']:
                        raise ValueError(f"Insufficient stock for Lens ID {item_data['lens']}.")
                    stock_updates.append(('lens', stock, item_data['quantity']))

                elif item_data.get('lens_cleaner'):
                    stock = LensCleanerStock.objects.select_for_update().filter(lens_cleaner_id=item_data['lens_cleaner']).first()
                    if not stock or stock.qty < item_data['quantity']:
                        raise ValueError(f"Insufficient stock for Lens Cleaner ID {item_data['lens_cleaner']}.")
                    stock_updates.append(('lens_cleaner', stock, item_data['quantity']))

                elif item_data.get('frame'):
                    stock = FrameStock.objects.select_for_update().filter(frame_id=item_data['frame']).first()
                    if not stock or stock.qty < item_data['quantity']:
                        raise ValueError(f"Insufficient stock for Frame ID {item_data['frame']}.")
                    stock_updates.append(('frame', stock, item_data['quantity']))

        return stock_updates  # Return stock updates for later processing
