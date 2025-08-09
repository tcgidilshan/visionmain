from ..models import Order,Frame,OrderProgress, OtherItem,OrderItem, LensStock, LensCleanerStock, FrameStock,Lens,LensCleaner,Frame,ExternalLens,OtherItemStock,BusSystemSetting, HearingItem, HearingItemStock
from ..serializers import OrderSerializer, OrderItemSerializer, ExternalLensSerializer
from django.db import transaction
from ..services.order_payment_service import OrderPaymentService
from ..services.external_lens_service import ExternalLensService
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from ..services.stock_validation_service import StockValidationService
from django.utils import timezone
from decimal import Decimal, InvalidOperation
class OrderService:
    """
    Handles order and order item creation.
    """
    @staticmethod
    @transaction.atomic
    def create_order(order_data, order_items_data):
        """
        Creates an order and its related order items.
        For on-hold orders: reduces frame stock but not lens stock.
        For regular orders: reduces both frame and lens stock.
        """
        # Step 1: Extract necessary fields
        on_hold = order_data.get("on_hold", False)
        branch_id = order_data.get("branch_id")
        invoice_type = order_data.get("invoice_type")
        
        if not branch_id:
            raise ValidationError({"branch_id": "Branch ID is required for stock validation."})

        # Step 2: Validate stock with on_hold flag
        # This returns separate updates for frames and lenses
        frame_stock_updates, lens_stock_updates = StockValidationService.validate_stocks(
            order_items_data, branch_id, on_hold=on_hold
        )

        # Step 3: Create the Order
        order_serializer = OrderSerializer(data=order_data)
        order_serializer.is_valid(raise_exception=True)
        order = order_serializer.save()

        # Step 4: Create the Order Items
        order_items = []
        for item_data in order_items_data:
            external_lens_id = item_data.get('external_lens')

            if external_lens_id:
                # Validate the ExternalLens exists
                if not ExternalLens.objects.filter(id=external_lens_id).exists():
                    raise ValidationError({'external_lens': f"ExternalLens with ID {external_lens_id} does not exist."})

            item_data['order'] = order.id  # Attach order reference
            order_item_serializer = OrderItemSerializer(data=item_data)
            order_item_serializer.is_valid(raise_exception=True)
            order_items.append(order_item_serializer.save())

        # Step 5: Adjust stocks based on on_hold status
        # Always adjust frame stock (even for on-hold orders)
        StockValidationService.adjust_stocks(frame_stock_updates)
        
        # Only adjust lens stock if NOT on hold
        if not on_hold:
            StockValidationService.adjust_stocks(lens_stock_updates)

       # Always create a new progress status with 'received_from_customer' as the initial status
        if invoice_type == "factory":
            OrderProgress.objects.create(
                order=order,
                progress_status=order_data.get("progress_status"),
            )
        # Step 6: Return the created order
        return order
    @staticmethod
    @transaction.atomic
    def on_change_append(existing_item: OrderItem, new_data: dict, admin_id: int, user_id: int):
        """
        Medical-compliant item update with append-on-change logic.
        1. If any tracked field changes: soft-delete old, create new (copying original order ref, user/admin).
        2. If not changed: just return original (do nothing).
        """
        TRACKED_FIELDS = [
            "price_per_unit", "subtotal", "external_lens", "lens", "frame",
            "lens_cleaner", "other_item", "note", "quantity", "hearing_item","serial_no","battery"
        ]
        FK_FIELDS = {
            'frame': Frame,
            'lens': Lens,
            'external_lens': ExternalLens,
            'lens_cleaner': LensCleaner,
            'other_item': OtherItem,
            'hearing_item': HearingItem,
        }

        # Always recalculate subtotal using Decimal (ignore frontend subtotal)
        if 'quantity' in new_data and 'price_per_unit' in new_data:
            try:
                q = Decimal(str(new_data['quantity']))
                p = Decimal(str(new_data['price_per_unit']))
                new_data['subtotal'] = q * p
            except Exception:
                new_data['subtotal'] = Decimal('0.00')

        changed = False

        # Detect field changes robustly
        for field in TRACKED_FIELDS:
            old = getattr(existing_item, field)
            new = new_data.get(field, old)
            if field in FK_FIELDS:
                old_id = getattr(old, 'id', old) if old else None
                new_id = new if isinstance(new, int) else getattr(new, 'id', new) if new else None
                if old_id != new_id:
                    changed = True
                    break
            elif field in ["price_per_unit", "subtotal"]:
                try:
                    old_val = Decimal(str(old)) if old is not None else None
                    new_val = Decimal(str(new)) if new is not None else None
                    if old_val != new_val:
                        changed = True
                        break
                except (InvalidOperation, TypeError):
                    if old != new:
                        changed = True
                        break
            elif field == "quantity":
                try:
                    if int(old) != int(new):
                        changed = True
                        break
                except Exception:
                    if old != new:
                        changed = True
                        break
            else:
                if old != new:
                    changed = True
                    break

        if changed:
            # //TODO: Soft-delete the old item for compliance
            existing_item.is_deleted = True
            existing_item.deleted_at = timezone.now()
            existing_item.admin_id = admin_id  
            existing_item.user_id = user_id
            existing_item.save()

            # //TODO: Prepare new item data with proper FK resolution
            new_item_data = {
                **new_data,
                "order": existing_item.order,
                "admin_id": admin_id,
                "user_id": user_id,
            }
            new_item_data.pop("id", None)  # Ensure id not reused

            # Resolve FK IDs to instances
            for field, model in FK_FIELDS.items():
                value = new_item_data.get(field)
                if value and not isinstance(value, model):
                    new_item_data[field] = model.objects.get(pk=value)
                elif not value:
                    new_item_data[field] = None

            # //TODO: Audit log creation could be inserted here for regulatory trace
            new_item = OrderItem.objects.create(**new_item_data)
            return new_item
        else:
            # No changes: keep as is, don't update or touch
            return existing_item

    @staticmethod
    @transaction.atomic
    def update_order(order, order_data, order_items_data, payments_data,admin_id,user_id):
        if order.is_deleted:
            raise ValidationError("This order has been deleted and cannot be modified.")

        """
        Updates an order along with its items and payments.
        Handles on-hold orders differently:
        - Frame stock is always adjusted immediately
        - Lens stock is only adjusted when the order is not on hold
        - When transitioning from on_hold=True to on_hold=False, lens stock is validated and deducted
        """

        try:
            branch_id = order.branch_id
            if not branch_id:
                raise ValueError("Order is not associated with a branch.")

            # Track on_hold flag changes
            was_on_hold = order.on_hold
            will_be_on_hold = order_data.get("on_hold", was_on_hold)
            # Detect transition from on-hold to active
            transitioning_off_hold = was_on_hold and not will_be_on_hold
            
            # Track existing items for later comparison
            existing_items = {item.id: item for item in order.order_items.all()}

            # If transitioning from on-hold to active, validate lens stock
            lens_stock_updates = []
            if transitioning_off_hold:
                # Get only the lens-related items (not frames) for validation
                # Skip external_lens since they don't maintain stock
                lens_items = []
                for item_data in order_items_data:
                    if (item_data.get('lens') or item_data.get('lens_cleaner') or 
                        item_data.get('other_item')) and not item_data.get('is_non_stock', False):
                        lens_items.append(item_data)
                
                # Only validate if there are actual stock items to validate
                if lens_items:
                    _, lens_stock_updates = StockValidationService.validate_stocks(
                        lens_items, branch_id, on_hold=False, existing_items=existing_items
                    )


            # Update order fields
            order.sub_total = order_data.get('sub_total', order.sub_total)
            order.discount = order_data.get('discount', order.discount)
            order.total_price = order_data.get('total_price', order.total_price)
            order.status = order_data.get('status', order.status)
            order.sales_staff_code_id = order_data.get('sales_staff_code', order.sales_staff_code_id)
            order.order_remark = order_data.get('order_remark', order.order_remark)
            order.user_date = order_data.get('user_date', order.user_date)
            order.on_hold = will_be_on_hold  # Update hold status
            order.fitting_on_collection = order_data.get('fitting_on_collection', order.fitting_on_collection)  # Update hold status
            bus_title_id = order_data.get('bus_title')
            #urgent
            order.urgent = order_data.get('urgent', order.urgent)

            #Update Progress Status
          # 1. Update the progress_status field (capture previous if needed)
            incoming_status = order_data.get('progress_status', None)
            last_progress = order.order_progress_status.order_by('-changed_at').first()
            # Always log if this is the first status, or if it's different from the last logged status
            if incoming_status and (
                last_progress is None or last_progress.progress_status != incoming_status
            ):
                OrderProgress.objects.create(
                    order=order,
                    progress_status=incoming_status,
                )
            
            if bus_title_id is not None:
                order.bus_title = BusSystemSetting.objects.get(pk=bus_title_id)
            
            for field in ['pd', 'height', 'right_height', 'left_height', 'left_pd', 'right_pd']:
                if field in order_data:
                    setattr(order, field, order_data.get(field))
            order.save()
            updated_item_ids = set()
            # Create/Update order items
            for item_data in order_items_data:
                item_id = item_data.get('id')
                is_non_stock = item_data.get('is_non_stock', False)
                quantity = item_data['quantity']
                new_quantity = int(item_data['quantity'])
                external_lens_id = item_data.get('external_lens')

                # Validate external lens
                if external_lens_id:
                    if not ExternalLens.objects.filter(id=external_lens_id).exists():
                        raise ValueError(f"External lens ID {external_lens_id} does not exist.")

                # Skip stock handling for non-stock items
                if is_non_stock:
                    # Just save the item
                    if item_id and item_id in existing_items:
                        # Update existing item
                        old_item = existing_items[item_id]
                        result_item = OrderService.on_change_append(old_item, item_data, admin_id, user_id)
                        updated_item_ids.add(result_item.id)
                        
                        
                    else:
                        # Create new item
                        hearing_item_id = item_data.get("hearing_item")
                        if hearing_item_id:
                            hearing_item = HearingItem.objects.get(pk=hearing_item_id)
                            OrderItem.objects.create(
                                order=order,
                                quantity=quantity,
                                price_per_unit=item_data['price_per_unit'],
                                subtotal=item_data['subtotal'],
                                external_lens_id=external_lens_id,
                                lens_id=item_data.get("lens"),
                                frame_id=item_data.get("frame"),
                                lens_cleaner_id=item_data.get("lens_cleaner"),
                                other_item_id=item_data.get("other_item"),
                                hearing_item=hearing_item,
                                is_non_stock=is_non_stock,
                                note=item_data.get("note"),
                                admin_id=None,
                                user_id=None
                            )
                        else:
                            OrderItem.objects.create(
                                order=order,
                                quantity=quantity,
                                price_per_unit=item_data['price_per_unit'],
                                subtotal=item_data['subtotal'],
                                external_lens_id=external_lens_id,
                                lens_id=item_data.get("lens"),
                                frame_id=item_data.get("frame"),
                                lens_cleaner_id=item_data.get("lens_cleaner"),
                                other_item_id=item_data.get("other_item"),
                                is_non_stock=is_non_stock,
                                note=item_data.get("note"),
                                admin_id=None,
                                user_id=None
                            )
                    continue

                # Handle stock for items (frame vs lens-related differently)
                stock = None
                stock_type = None
                is_frame = False

                # Determine stock type and get stock object
                if item_data.get("lens"):
                    stock = LensStock.objects.select_for_update().filter(lens_id=item_data["lens"], branch_id=branch_id).first()
                    stock_type = "lens"
                elif item_data.get("frame"):
                    stock = FrameStock.objects.select_for_update().filter(frame_id=item_data["frame"], branch_id=branch_id).first()
                    stock_type = "frame"
                    is_frame = True
                elif item_data.get("other_item"):
                    stock = OtherItemStock.objects.select_for_update().filter(other_item_id=item_data["other_item"], branch_id=branch_id).first()
                    stock_type = "other_item"
                elif item_data.get("lens_cleaner"):
                    stock = LensCleanerStock.objects.select_for_update().filter(lens_cleaner_id=item_data["lens_cleaner"], branch_id=branch_id).first()
                    stock_type = "lens_cleaner"
                elif item_data.get("hearing_item"):
                    stock = HearingItemStock.objects.select_for_update().filter(hearing_item_id=item_data["hearing_item"], branch_id=branch_id).first()
                    stock_type = "hearing_item"

                if not stock:
                    raise ValueError(f"{stock_type.capitalize()} stock not found for branch {branch_id}.")

                # Only adjust lens-related stock if NOT on hold (or frame stock always)
                should_adjust_stock = is_frame or not will_be_on_hold

                if should_adjust_stock:
                    if item_id and item_id in existing_items:
                        # Update existing item
                       old_item = existing_items[item_id]
                       if int(old_item.quantity) != new_quantity:
                          if stock.qty < new_quantity:
                            raise ValueError(f"Insufficient {stock_type} stock.")
                          stock.qty -= new_quantity
                          stock.save()
                    else:
                        # Create new item

                        if stock.qty < quantity:
                            
                            raise ValueError(f"Insufficient {stock_type} stock.")
                        stock.qty -= new_quantity
                        stock.save()

                # Save order item
                if item_id and item_id in existing_items:
                    old_item = existing_items[item_id]
                    result_item = OrderService.on_change_append(old_item, item_data, admin_id, user_id)
                    updated_item_ids.add(result_item.id)
                else:
                    hearing_item_id = item_data.get("hearing_item")
                    if hearing_item_id:
                        hearing_item = HearingItem.objects.get(pk=hearing_item_id)
                        OrderItem.objects.create(
                            order=order,
                            quantity=quantity,
                            price_per_unit=item_data['price_per_unit'],
                            subtotal=item_data['subtotal'],
                            external_lens_id=external_lens_id,
                            lens_id=item_data.get("lens"),
                            frame_id=item_data.get("frame"),
                            lens_cleaner_id=item_data.get("lens_cleaner"),
                            other_item_id=item_data.get("other_item"),
                            hearing_item=hearing_item,
                            is_non_stock=is_non_stock,
                            note=item_data.get("note"),
                            admin_id=None,
                            user_id=None
                        )
                    else:
                        OrderItem.objects.create(
                            order=order,
                            quantity=quantity,
                            price_per_unit=item_data['price_per_unit'],
                            subtotal=item_data['subtotal'],
                            external_lens_id=external_lens_id,
                            lens_id=item_data.get("lens"),
                            frame_id=item_data.get("frame"),
                            lens_cleaner_id=item_data.get("lens_cleaner"),
                            other_item_id=item_data.get("other_item"),
                            is_non_stock=is_non_stock,
                            note=item_data.get("note"),
                            admin_id=None,
                            user_id=None
                        )

            # Handle deleted items and restock
            # //TODO: CLEANUP DELETED ORDER ITEMS (soft delete and restock if needed)
            for item_id, deleted_item in existing_items.items():
                if item_id not in updated_item_ids:
                    if not deleted_item.is_non_stock:
                        stock = None
                        stock_model = None
                        stock_filter = {}
                        is_frame = False

                        if deleted_item.lens_id:
                            stock_model = LensStock
                            stock_filter = {"lens_id": deleted_item.lens_id, "branch_id": branch_id}
                        elif deleted_item.frame_id:
                            stock_model = FrameStock
                            stock_filter = {"frame_id": deleted_item.frame_id, "branch_id": branch_id}
                            is_frame = True
                        elif deleted_item.lens_cleaner_id:
                            stock_model = LensCleanerStock
                            stock_filter = {"lens_cleaner_id": deleted_item.lens_cleaner_id, "branch_id": branch_id}
                        elif deleted_item.other_item_id:
                            stock_model = OtherItemStock
                            stock_filter = {"other_item_id": deleted_item.other_item_id, "branch_id": branch_id}

                        should_restock = is_frame or not will_be_on_hold

                        if should_restock and stock_model and stock_filter:
                            stock = stock_model.objects.select_for_update().filter(**stock_filter).first()
                            if stock:
                                stock.qty += deleted_item.quantity
                                stock.save()
                            elif stock_model:
                                raise ValueError(
                                    f"Stock record not found for deleted item [{stock_model.__name__}] in branch {branch_id} "
                                    f"(Item ID: {deleted_item.id})"
                                )
                            else:
                                raise ValueError(
                                    f"⚠️ Warning: Item ID {deleted_item.id} marked as stock, but has no stock FK set "
                                    f"(lens, frame, other_item, or lens_cleaner). Skipping restock."
                                )
                    deleted_item.delete()


            # Final: Deduct lens stock if on_hold → False
            if transitioning_off_hold:
                StockValidationService.adjust_stocks(lens_stock_updates)

            # Process Payments
            total_payment = OrderPaymentService.append_on_change_payments_for_order(order, payments_data,admin_id,user_id)
            if total_payment > order.total_price:
                raise ValueError("Total payments exceed the order total price.")

            return order

        except ExternalLens.DoesNotExist:
            raise ValueError("Invalid External Lens ID.")
        except Exception as e:
            transaction.set_rollback(True)
            raise ValueError(f"Order update failed: {str(e)}")