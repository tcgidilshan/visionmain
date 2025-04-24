from ..models import Order, OrderItem, LensStock, LensCleanerStock, FrameStock,Lens,LensCleaner,Frame,ExternalLens,OtherItemStock
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
    def create_order(order_data, order_items_data):
        """
        Creates an order and its related order items.
        References external lenses by ID only (no creation).
        Raises validation errors if invalid IDs are passed.
        """
        # Step 1: Create the Order
        order_serializer = OrderSerializer(data=order_data)
        order_serializer.is_valid(raise_exception=True)
        order = order_serializer.save()

        # Step 2: Create the Order Items
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

        return order  # Return the created order
    
    @staticmethod
    @transaction.atomic
    def update_order(order, order_data, order_items_data, payments_data):
        """
        Updates an order along with its items and payments.
        External lenses are now referenced by ID only — no creation or modification.
        Stock updates and deletions handled inline.
        """
        try:
            branch_id = order.branch_id
            if not branch_id:
                raise ValueError("Order is not associated with a branch.")

            existing_items = {item.id: item for item in order.order_items.all()}

            # Update order fields
            order.sub_total = order_data.get('sub_total', order.sub_total)
            order.discount = order_data.get('discount', order.discount)
            order.total_price = order_data.get('total_price', order.total_price)
            order.status = order_data.get('status', order.status)
            order.sales_staff_code_id = order_data.get('sales_staff_code', order.sales_staff_code_id)
            order.order_remark = order_data.get('order_remark', order.order_remark)
            order.save()

            for item_data in order_items_data:
                item_id = item_data.get('id')
                is_non_stock = item_data.get('is_non_stock', False)
                quantity = item_data['quantity']

                # ✅ Validate external lens if provided
                external_lens_id = item_data.get('external_lens')
                if external_lens_id:
                    if not ExternalLens.objects.filter(id=external_lens_id).exists():
                        raise ValueError(f"External lens ID {external_lens_id} does not exist.")

                # Handle stock
                stock = None
                stock_type = None

                if not is_non_stock:
                    if item_data.get("lens"):
                        stock = LensStock.objects.select_for_update().filter(lens_id=item_data["lens"], branch_id=branch_id).first()
                        stock_type = "lens"
                    elif item_data.get("frame"):
                        stock = FrameStock.objects.select_for_update().filter(frame_id=item_data["frame"], branch_id=branch_id).first()
                        stock_type = "frame"
                    elif item_data.get("other_item"):
                        stock = OtherItemStock.objects.select_for_update().filter(other_item_id=item_data["other_item"], branch_id=branch_id).first()
                        stock_type = "other_item"
                    elif item_data.get("lens_cleaner"):
                        stock = LensCleanerStock.objects.select_for_update().filter(lens_cleaner_id=item_data["lens_cleaner"], branch_id=branch_id).first()
                        stock_type = "lens_cleaner"

                    if not stock:
                        raise ValueError(f"{stock_type.capitalize()} stock not found for branch {branch_id}.")

                    if item_id and item_id in existing_items:
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
                        if stock.qty < quantity:
                            raise ValueError(f"Insufficient {stock_type} stock.")
                        stock.qty -= quantity
                        stock.save()

                # Create or update the item
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
                        other_item_id=item_data.get("other_item")
                    )

            # ✅ Handle deletions with safe restocking
            for deleted_item in existing_items.values():
                if not deleted_item.is_non_stock:
                    stock = None
                    stock_model = None

                    if deleted_item.lens_id:
                        stock_model = LensStock
                        stock = LensStock.objects.select_for_update().filter(
                            lens_id=deleted_item.lens_id,
                            branch_id=branch_id
                        ).first()
                    elif deleted_item.frame_id:
                        stock_model = FrameStock
                        stock = FrameStock.objects.select_for_update().filter(
                            frame_id=deleted_item.frame_id,
                            branch_id=branch_id
                        ).first()
                    elif deleted_item.lens_cleaner_id:
                        stock_model = LensCleanerStock
                        stock = LensCleanerStock.objects.select_for_update().filter(
                            lens_cleaner_id=deleted_item.lens_cleaner_id,
                            branch_id=branch_id
                        ).first()
                    elif deleted_item.other_item_id:
                        stock_model = OtherItemStock
                        stock = OtherItemStock.objects.select_for_update().filter(
                            other_item_id=deleted_item.other_item_id,
                            branch_id=branch_id
                        ).first()

                    if stock:
                        stock.qty += deleted_item.quantity
                        stock.save()
                    else:
                        raise ValueError(
                            f"Stock record not found for deleted item "
                            f"[{stock_model.__name__ if stock_model else 'Unknown'}] "
                            f"in branch {branch_id}"
                        )

                # ✅ Always delete after restocking
                deleted_item.delete()

            # Payments
            total_payment = OrderPaymentService.update_process_payments(order, payments_data)
            if total_payment > order.total_price:
                raise ValueError("Total payments exceed the order total price.")

            return order

        except ExternalLens.DoesNotExist:
            raise ValueError("Invalid External Lens ID.")
        except Exception as e:
            transaction.set_rollback(True)
            raise ValueError(f"Order update failed: {str(e)}")
