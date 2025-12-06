from ..models import (
    FrameStock, LensStock, OtherItemStock, LensCleanerStock, HearingItemStock
)
from django.utils import timezone
from django.db import transaction

class StockRollbackService:

    @staticmethod
    @transaction.atomic
    def rollback_stock(order_items, branch_id, on_hold):
        """
        Rolls back stock for all item types in the order:
        - Frame stock: always
        - Lens stock: only if not on_hold
        - Other item stock: always
        - Lens cleaner stock: always
        - Hearing item stock: always
        """
        for item in order_items:
            qty = item.quantity

            if item.frame_id:
                StockRollbackService.increment_frame_stock(item.frame_id, qty, branch_id)

            if not on_hold and item.lens_id:
                StockRollbackService.increment_lens_stock(item.lens_id, qty, branch_id)

            if item.other_item_id:
                StockRollbackService.increment_other_item_stock(item.other_item_id, qty, branch_id)

            if item.lens_cleaner_id:
                StockRollbackService.increment_lens_cleaner_stock(item.lens_cleaner_id, qty, branch_id)

            if item.hearing_item_id:
                StockRollbackService.increment_hearing_item_stock(item.hearing_item_id, qty, branch_id)

    @staticmethod
    def increment_frame_stock(frame_id, quantity, branch_id):
        stock = FrameStock.objects.select_for_update().get(frame_id=frame_id, branch_id=branch_id)
        stock.qty += quantity
        stock.last_updated = timezone.now()
        stock.save()

    @staticmethod
    def increment_lens_stock(lens_id, quantity, branch_id):
        stock = LensStock.objects.select_for_update().get(lens_id=lens_id, branch_id=branch_id)
        stock.qty += quantity
        stock.last_updated = timezone.now()
        stock.save()

    @staticmethod
    def increment_other_item_stock(item_id, quantity, branch_id):
        stock = OtherItemStock.objects.select_for_update().get(other_item_id=item_id, branch_id=branch_id)
        stock.qty += quantity
        stock.last_updated = timezone.now()
        stock.save()

    @staticmethod
    def increment_lens_cleaner_stock(item_id, quantity, branch_id):
        stock = LensCleanerStock.objects.select_for_update().get(lens_cleaner_id=item_id, branch_id=branch_id)
        stock.qty += quantity
        stock.last_updated = timezone.now()
        stock.save()

    @staticmethod
    def increment_hearing_item_stock(item_id, quantity, branch_id):
        stock = HearingItemStock.objects.select_for_update().get(hearing_item_id=item_id, branch_id=branch_id)
        stock.qty += quantity
        stock.last_updated = timezone.now()
        stock.save()
