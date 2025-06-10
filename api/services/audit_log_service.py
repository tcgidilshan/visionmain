from decimal import Decimal, InvalidOperation
from django.utils.timezone import now
from ..models import OrderAuditLog, CustomUser


class OrderAuditLogService:
    """
    Service to track changes in specific Order fields and log them to OrderAuditLog.
    Handles decimals, booleans, and nullable fields carefully.
    """

    TRACKED_FIELDS = {
        'urgent', 'pd', 'height', 'right_height', 'left_height',
        'left_pd', 'right_pd', 'order_remark', 'sub_total', 'discount','total_price'
    }

    @staticmethod
    #type safty jsut in case frontend sends wrong data types
    def normalize_value(field, value):
        if value is None:
            return None

        if field in {'sub_total', 'discount', 'total_price'}:
            try:
                return Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                return None
        if field in {'pd', 'height', 'right_height', 'left_height', 'left_pd', 'right_pd', 'order_remark'}:
            value = str(value).strip() if isinstance(value, str) else value
            return value if value != "" else None
        
        if field == 'urgent':
            return bool(value)



    @staticmethod
    def log_order_changes(order_instance, updated_data: dict, original_data: dict, raw_data: dict):
        admin_id = raw_data.get('admin_id')
        user_id = raw_data.get('user_id')
        admin = CustomUser.objects.filter(id=admin_id).first() if admin_id else None
        user = CustomUser.objects.filter(id=user_id).first() if user_id else None

        for field in OrderAuditLogService.TRACKED_FIELDS:
            if field not in updated_data:
                continue

            new_value = OrderAuditLogService.normalize_value(field, updated_data[field])
            old_value = OrderAuditLogService.normalize_value(field, original_data.get(field, None))

            if new_value != old_value:
                OrderAuditLog.objects.create(
                    order=order_instance,
                    field_name=field,
                    old_value=str(old_value) if old_value is not None else '',
                    new_value=str(new_value) if new_value is not None else '',
                    admin=admin,
                    user=user,
                    created_at=now()
                )
