from django.db import transaction
from ..models import LensStock, LensCleanerStock, FrameStock, OtherItemStock

class StockValidationService:
    """
    Service to handle stock validation for orders, scoped by branch.
    Enhanced to handle on-hold orders differently for frame and lens stock.
    """

    @staticmethod
    def validate_stocks(order_items_data, branch_id, on_hold=False, existing_items=None):
        """
        Validates branch-specific stock availability for given order items.
        For on-hold orders: validates all stock but separates frame stock and lens-related stock.
        Raises ValueError if stock is insufficient.
        Returns a tuple of (frame_stock_updates, lens_stock_updates).
        """
        if not order_items_data:
            raise ValueError("Order items are required.")

        if not branch_id:
            raise ValueError("Branch ID is required for stock validation.")

        frame_stock_updates = []  # List to track frame stock changes
        lens_stock_updates = []   # List to track lens and other stock changes

        with transaction.atomic():
            for item_data in order_items_data:
                if item_data.get('is_non_stock', False):  # ✅ Skip non-stock items
                    continue

                stock = None
                stock_type = None

                # Determine item ID and existing quantity if available
                item_id = item_data.get('id')
                existing_qty = 0
                if existing_items and item_id and item_id in existing_items:
                    existing_qty = existing_items[item_id].quantity

                new_qty = item_data['quantity']
                effective_qty = new_qty - existing_qty

                # ✅ Skip validation if no additional stock is needed
                if effective_qty <= 0:
                    continue

                # Process lens-related items
                if item_data.get('lens'):
                    stock = LensStock.objects.select_for_update().filter(
                        lens_id=item_data['lens'],
                        branch_id=branch_id
                    ).first()
                    stock_type = 'lens'

                elif item_data.get('lens_cleaner'):
                    stock = LensCleanerStock.objects.select_for_update().filter(
                        lens_cleaner_id=item_data['lens_cleaner'],
                        branch_id=branch_id
                    ).first()
                    stock_type = 'lens_cleaner'

                elif item_data.get('frame'):
                    stock = FrameStock.objects.select_for_update().filter(
                        frame_id=item_data['frame'],
                        branch_id=branch_id
                    ).first()
                    stock_type = 'frame'

                elif item_data.get('other_item'):
                    stock = OtherItemStock.objects.select_for_update().filter(
                        other_item_id=item_data['other_item'],
                        branch_id=branch_id
                    ).first()
                    stock_type = 'other_item'

                if not stock:
                    raise ValueError(f"{stock_type.capitalize()} stock not found for branch {branch_id}.")

                if stock.qty < effective_qty:
                    raise ValueError(f"Insufficient stock for {stock_type} ID {item_data.get(stock_type)} in branch {branch_id}.")

                # Track for future deduction
                if stock_type == 'frame':
                    frame_stock_updates.append((stock_type, stock, effective_qty))
                else:
                    lens_stock_updates.append((stock_type, stock, effective_qty))

        return frame_stock_updates, lens_stock_updates


    @staticmethod
    def adjust_stocks(stock_updates):
        """
        Adjusts stock quantities after a successful order.
        """
        with transaction.atomic():
            for stock_type, stock, quantity in stock_updates:
                stock.qty -= quantity
                stock.save()