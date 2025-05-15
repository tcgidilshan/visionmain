from django.db import transaction
from django.utils import timezone
from ..models import Order, OrderItem, Invoice, OrderPayment
from .rollback_service import StockRollbackService  # hypothetical
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist

class OrderSoftDeleteService:

    @staticmethod
    @transaction.atomic
    def soft_delete_order(order_id, deleted_by=None, reason=None):
        try:
            order = Order.all_objects.select_related().prefetch_related(
                'order_items', 'invoice', 'orderpayment_set'
            ).get(id=order_id)

            if order.is_deleted:
                raise ValidationError("Order is already deleted.")

            now = timezone.now()

            # 🔁 Rollback stock
            StockRollbackService.rollback_stock(
                order_items=order.order_items.filter(is_deleted=False),
                branch_id=order.branch_id,
                on_hold=order.on_hold
            )

            # Order Items
            for item in order.order_items.all():
                item.is_deleted = True
                item.deleted_at = now
                item.save()

            # Soft delete related Invoice (one-to-one)
            try:
                invoice = order.invoice  # related_name="invoice"
                invoice.is_deleted = True
                invoice.deleted_at = now
                invoice.save()
            except ObjectDoesNotExist:
                pass  # No invoice exists — safe to ignore

            # Payments
            for payment in order.orderpayment_set.all():
                payment.is_deleted = True
                payment.deleted_at = now
                payment.save()

            # 🧾 Update order fields
            order.is_deleted = True
            order.deleted_at = now
            if hasattr(order, 'deleted_by') and deleted_by:
                order.deleted_by = deleted_by
            if hasattr(order, 'deleted_reason') and reason:
                order.deleted_reason = reason
            if hasattr(order, 'status'):
                order.status = 'cancelled'
            order.save()

            return order

        except Order.DoesNotExist:
            raise ValidationError("Order not found.")
