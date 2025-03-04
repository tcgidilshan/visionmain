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
                if item_data.get('is_non_stock', False):  # ✅ Skip stock validation for non-stock items
                    continue  

                stock = None
                stock_type = None

                if item_data.get('lens'):
                    stock = LensStock.objects.select_for_update().filter(lens_id=item_data['lens']).first()
                    stock_type = 'lens'
                elif item_data.get('lens_cleaner'):
                    stock = LensCleanerStock.objects.select_for_update().filter(lens_cleaner_id=item_data['lens_cleaner']).first()
                    stock_type = 'lens_cleaner'
                elif item_data.get('frame'):
                    stock = FrameStock.objects.select_for_update().filter(frame_id=item_data['frame']).first()
                    stock_type = 'frame'

                if not stock or stock.qty < item_data['quantity']:
                    raise ValueError(f"Insufficient stock for {stock_type} ID {item_data.get(stock_type)}.")

                stock_updates.append((stock_type, stock, item_data['quantity']))

        return stock_updates  # ✅ Return stock updates for later processing
    
    @staticmethod
    def adjust_stocks(stock_updates):
        """
        Adjusts stock quantities after an order is successfully created.
        """
        with transaction.atomic():
            for stock_type, stock, quantity in stock_updates:
                stock.qty -= quantity
                stock.save()
