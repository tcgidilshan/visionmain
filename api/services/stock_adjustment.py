# inventory/services/stock_adjustment.py

from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Frame, FrameStock, FrameStockHistory

def adjust_stock_bulk(action, items, branch, performed_by):
    """
    Adjust stock for multiple frames at a given branch.
    
    :param action: "add" or "remove"
    :param items: list of dicts: [{ "frame_id": int, "quantity": int }]
    :param branch: Branch instance
    :param performed_by: User instance
    :raises: ValidationError if any operation would fail
    :return: list of updated FrameStock objects
    """

    if action not in ['add', 'remove']:
        raise ValidationError(f"Invalid action: {action}. Must be 'add' or 'remove'.")

    updated_stocks = []

    with transaction.atomic():
        for item in items:
            frame_id = item.get('frame_id')
            quantity = item.get('quantity')

            if not frame_id or quantity is None:
                raise ValidationError("Each item must include 'frame_id' and 'quantity'.")

            try:
                frame = Frame.objects.get(id=frame_id)
            except Frame.DoesNotExist:
                raise ValidationError(f"Frame with ID {frame_id} does not exist.")

            stock, created = FrameStock.objects.get_or_create(
                frame=frame,
                branch=branch,
                defaults={'qty': 0}
            )

            # Stock logic
            if action == 'add':
                stock.qty += quantity
            elif action == 'remove':
                if stock.qty < quantity:
                    raise ValidationError(
                        f"Not enough stock for Frame ID {frame_id} at Branch {branch}. Available: {stock.qty}, requested: {quantity}"
                    )
                stock.qty -= quantity

            stock.save()
            updated_stocks.append(stock)

            # Log history
            FrameStockHistory.objects.create(
                frame=frame,
                branch=branch,
                action=action,
                quantity_changed=quantity,
                performed_by=performed_by
            )

    return
