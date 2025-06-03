from django.db import transaction
from django.core.exceptions import ValidationError
from api.models import MntOrder, Order, CustomUser, Branch

class MntOrderService:
    @staticmethod
    @transaction.atomic
    def create_mnt_order(order, user_id=None, admin_id=None):
        """
        Creates a new MntOrder for the given order.
        Ensures branch-wise MNT numbering, full audit, and medical compliance.
        """
        #TODO: Only allow for factory orders if needed
        if not order.branch:
            raise ValidationError("Order must be associated with a branch to create an MNT.")

        # Initialize user and admin as None
        user = None
        admin = None

        # If user/admin are passed as IDs, fetch them
        if user_id and isinstance(user_id, int):
            user = CustomUser.objects.filter(id=user_id).first()
        if admin_id and isinstance(admin_id, int):
            admin = CustomUser.objects.filter(id=admin_id).first()

        # Create and return the MNT order (number is auto-generated in model.save)
        mnt_order = MntOrder.objects.create(
            order=order,
            branch=order.branch,
            user=user,  # Pass the user object, not the ID
            admin=admin,  # Pass the admin object, not the ID
        )
        return mnt_order

    @staticmethod
    def get_mnt_orders_for_order(order):
        """
        Returns all MNT orders for a given order, ordered by created_at.
        """
        return MntOrder.objects.filter(order=order).order_by('created_at')

    @staticmethod
    def get_latest_mnt_order_for_order(order):
        """
        Returns the latest (most recent) MNT order for a given order.
        """
        return MntOrder.objects.filter(order=order).order_by('-created_at').first()

    @staticmethod
    def is_mnt_allowed(order):
        """
        Checks if MNT creation is allowed (e.g., only for 'factory' type orders).
        Customize as needed.
        """
        # Example: only allow for factory orders
        if hasattr(order, 'invoice') and order.invoice.invoice_type != 'factory':
            return False
        return True
