from django.db import transaction
from django.utils import timezone
from ..models import Order, OrderItem, Invoice, OrderPayment,Appointment, Schedule, ChannelPayment
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
            # for payment in order.orderpayment_set.all():
            #     payment.is_deleted = True
            #     payment.deleted_at = now
            #     payment.save()

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
        
class ChannelSoftDeleteService:
    @staticmethod
    @transaction.atomic
    def soft_delete_channel(appointment_id):
        try:
            appointment = Appointment.all_objects.select_related('schedule').get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ValueError("Appointment not found.")

        if appointment.is_deleted:
            raise ValueError("Appointment is already deleted.")

        # Step 1: Soft delete Appointment
        appointment.is_deleted = True
        appointment.deleted_at = timezone.now()
        appointment.save()

        # Step 2: Soft delete related payments
        ChannelPayment.objects.filter(appointment_id=appointment.id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now()
        )

        # Step 3: Optionally free up Schedule (if still valid)
        if appointment.schedule and not appointment.schedule.is_deleted:
            appointment.schedule.is_deleted = True
            appointment.schedule.deleted_at = timezone.now()
            appointment.schedule.status = 'Available'
            appointment.schedule.save()

        return {
            "message": "Channel soft deleted successfully.",
            "appointment_id": appointment.id
        }
