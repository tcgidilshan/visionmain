from decimal import Decimal, InvalidOperation
from django.utils.timezone import now
from ..models import OrderAuditLog, CustomUser,RefractionDetailsAuditLog

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

class RefractionDetailsAuditLogService:
    """
    Service to track changes in RefractionDetails fields and log them.
    Ensures consistent formatting, handles nullable & boolean fields.
    """

    TRACKED_FIELDS = {
        # Clinical measurements & text
        'hb_rx_right_dist', 'hb_rx_left_dist', 'hb_rx_right_near', 'hb_rx_left_near',
        'auto_ref_right', 'auto_ref_left', 'ntc_right', 'ntc_left',
        'va_without_glass_right', 'va_without_glass_left',
        'va_without_ph_right', 'va_without_ph_left',
        'va_with_glass_right', 'va_with_glass_left',
        'right_eye_dist_sph', 'right_eye_dist_cyl', 'right_eye_dist_axis', 'right_eye_near_sph',
        'left_eye_dist_sph', 'left_eye_dist_cyl', 'left_eye_dist_axis', 'left_eye_near_sph',
        'note', 'refraction_remark',

        # Booleans
        'cataract', 'blepharitis', 'shuger', 'is_manual',

        # Choice field
        'prescription_type',
    }

    @staticmethod
    def normalize_value(field, value):
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if field in {'cataract', 'blepharitis', 'shuger', 'is_manual'}:
            return bool(value)

        return str(value).strip() if isinstance(value, str) else value

    @staticmethod
    def log_changes(instance, updated_data: dict, original_data: dict, raw_data: dict):
        admin_id = raw_data.get("admin_id")
        user_id = raw_data.get("user_id")
        admin = CustomUser.objects.filter(id=admin_id).first() if admin_id else None
        user = CustomUser.objects.filter(id=user_id).first() if user_id else None

        for field in RefractionDetailsAuditLogService.TRACKED_FIELDS:
            if field not in updated_data:
                continue

            new_value = RefractionDetailsAuditLogService.normalize_value(field, updated_data.get(field))
            old_value = RefractionDetailsAuditLogService.normalize_value(field, original_data.get(field))

            if new_value != old_value:
                RefractionDetailsAuditLog.objects.create(
                    refraction_details=instance,
                    field_name=field,
                    old_value=str(old_value) if old_value is not None else '',
                    new_value=str(new_value) if new_value is not None else '',
                    admin=admin,
                    user=user,
                    created_at=now()
                )
