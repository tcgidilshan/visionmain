from ..models import Order, OrderItem, LensStock, LensCleanerStock, FrameStock,Lens,LensCleaner,Frame,ExternalLens,OtherItemStock,BusSystemSetting
from ..serializers import OrderSerializer, OrderItemSerializer, ExternalLensSerializer
from django.db import transaction
from ..services.order_payment_service import OrderPaymentService
from ..services.external_lens_service import ExternalLensService
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from ..services.stock_validation_service import StockValidationService

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

        # Step 6: Return the created order
        return order
    
    @staticmethod
    @transaction.atomic
    def update_order(order, order_data, order_items_data, payments_data):
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

            # 🔹 Track on_hold flag changes
            was_on_hold = order.on_hold
            will_be_on_hold = order_data.get("on_hold", was_on_hold)
            
            # Detect transition from on-hold to active
            transitioning_off_hold = was_on_hold and not will_be_on_hold
            
            # Track existing items for later comparison
            existing_items = {item.id: item for item in order.order_items.all()}

            # 🔹 If transitioning from on-hold to active, validate lens stock
            lens_stock_updates = []
            if transitioning_off_hold:
                # Get only the lens-related items (not frames) for validation
                lens_items = []
                for item_data in order_items_data:
                    if (item_data.get('lens') or item_data.get('lens_cleaner') or 
                        item_data.get('other_item')) and not item_data.get('is_non_stock', False):
                        lens_items.append(item_data)
                
                # Validate lens stock separately
                _, lens_stock_updates = StockValidationService.validate_stocks(lens_items, branch_id, on_hold=False)

            # 🔹 Update order fields
            order.sub_total = order_data.get('sub_total', order.sub_total)
            order.discount = order_data.get('discount', order.discount)
            order.total_price = order_data.get('total_price', order.total_price)
            order.status = order_data.get('status', order.status)
            order.sales_staff_code_id = order_data.get('sales_staff_code', order.sales_staff_code_id)
            order.order_remark = order_data.get('order_remark', order.order_remark)
            order.user_date = order_data.get('user_date', order.user_date)
            order.on_hold = will_be_on_hold  # ✅ Update hold status
            bus_title_id = order_data.get('bus_title')
            if bus_title_id is not None:
                order.bus_title = BusSystemSetting.objects.get(pk=bus_title_id)
            

            for field in ['pd', 'height', 'right_height', 'left_height', 'left_pd', 'right_pd']:
                if field in order_data:
                    setattr(order, field, order_data.get(field))

            order.save()

            # 🔹 Create/Update order items
            for item_data in order_items_data:
                item_id = item_data.get('id')
                is_non_stock = item_data.get('is_non_stock', False)
                quantity = item_data['quantity']
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
                        existing_item = existing_items.pop(item_id)
                        existing_item.quantity = quantity
                        existing_item.price_per_unit = item_data['price_per_unit']
                        existing_item.subtotal = item_data['subtotal']
                        existing_item.external_lens_id = external_lens_id or existing_item.external_lens_id
                        existing_item.lens_id = item_data.get("lens", existing_item.lens_id)
                        existing_item.frame_id = item_data.get("frame", existing_item.frame_id)
                        existing_item.lens_cleaner_id = item_data.get("lens_cleaner", existing_item.lens_cleaner_id)
                        existing_item.other_item_id = item_data.get("other_item", existing_item.other_item_id)
                        existing_item.note = item_data.get("note", existing_item.note)
                        existing_item.save()
                    else:
                        # Create new item
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
                            note=item_data.get("note")
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

                if not stock:
                    raise ValueError(f"{stock_type.capitalize()} stock not found for branch {branch_id}.")

                # Only adjust lens-related stock if NOT on hold (or frame stock always)
                should_adjust_stock = is_frame or not will_be_on_hold

                if should_adjust_stock:
                    if item_id and item_id in existing_items:
                        # Update existing item
                        old_qty = existing_items[item_id].quantity
                        if quantity > old_qty:
                            diff = quantity - old_qty
                            if stock.qty < diff:
                                raise ValueError(f"Insufficient {stock_type} stock for increase.")
                            stock.qty -= diff
                        elif quantity < old_qty:
                            stock.qty += old_qty - quantity
                        stock.save()
                    else:
                        # Create new item
                        if stock.qty < quantity:
                            raise ValueError(f"Insufficient {stock_type} stock.")
                        stock.qty -= quantity
                        stock.save()

                # Save order item
                if item_id and item_id in existing_items:
                    existing_item = existing_items.pop(item_id)
                    existing_item.quantity = quantity
                    existing_item.price_per_unit = item_data['price_per_unit']
                    existing_item.subtotal = item_data['subtotal']
                    existing_item.external_lens_id = external_lens_id or existing_item.external_lens_id
                    existing_item.lens_id = item_data.get("lens", existing_item.lens_id)
                    existing_item.frame_id = item_data.get("frame", existing_item.frame_id)
                    existing_item.lens_cleaner_id = item_data.get("lens_cleaner", existing_item.lens_cleaner_id)
                    existing_item.other_item_id = item_data.get("other_item", existing_item.other_item_id)
                    existing_item.note = item_data.get("note", existing_item.note)
                    existing_item.save()
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
                        note=item_data.get("note")
                    )

            # 🔹 Handle deleted items and restock
            for deleted_item in existing_items.values():
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

                    # Only restock if it's a frame or if the order is not on hold
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
                            print(
                                f"⚠️ Warning: Item ID {deleted_item.id} marked as stock, but has no stock FK set "
                                f"(lens, frame, other_item, or lens_cleaner). Skipping restock."
                            )

                deleted_item.delete()

            # 🔹 Final: Deduct lens stock if on_hold → False
            if transitioning_off_hold:
                StockValidationService.adjust_stocks(lens_stock_updates)

            # 🔹 Process Payments
            total_payment = OrderPaymentService.update_process_payments(order, payments_data)
            if total_payment > order.total_price:
                raise ValueError("Total payments exceed the order total price.")

            return order

        except ExternalLens.DoesNotExist:
            raise ValueError("Invalid External Lens ID.")
        except Exception as e:
            transaction.set_rollback(True)
            raise ValueError(f"Order update failed: {str(e)}")