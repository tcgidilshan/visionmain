from django.db import transaction
from ..models import LensStock, LensCleanerStock, FrameStock, OtherItemStock

class StockAvilabilityService:
    """
    Service to handle stock validation for orders, scoped by branch.
    Enhanced to handle on-hold orders differently for frame and lens stock.
    """

    @staticmethod
    def check_stock_avilability(order_items_data, branch_id, existing_items=None):
        """
        Validates branch-specific stock availability for given order items.
        Returns a list of (stock, quantity_to_deduct) for successful validations.
        existing_items should be a list of OrderItem objects.
        """
        if not order_items_data:
            raise ValueError("Order items are required.")

        if not branch_id:
            raise ValueError("Branch ID is required for stock validation.")

        stock_updates = []

        with transaction.atomic():
            for item_data in order_items_data:
                if item_data.get('external_lens', None):  # ✅ Skip non-stock items
                    continue

                stock = None
                stock_type = None

                # Determine item ID and existing quantity if available
                item_id = item_data.get('id', None)
                existing_qty = 0  # Default for new items
                if item_id:
                    # Find existing item by ID in the list
                    existing_item = next((item for item in existing_items if item.id == item_id), None)
                    if existing_item:
                        existing_qty = existing_item.quantity

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

                # Collect stock update for later adjustment
                stock_updates.append((stock, effective_qty))

        return stock_updates


    @staticmethod
    def adjust_stocks(stock_updates):
        """
        Adjusts stock quantities after a successful order.
        stock_updates: list of (stock, quantity_to_deduct)
        """
        with transaction.atomic():
            for stock, quantity in stock_updates:
                stock.qty -= quantity
                stock.save()