from ..models import Order, OrderItem, LensStock, LensCleanerStock, FrameStock,Lens,LensCleaner,Frame,ExternalLens
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
        Raises validation errors if any issues occur.
        Returns the created order instance.
        """
        # Step 1: Create Order
        order_serializer = OrderSerializer(data=order_data)
        order_serializer.is_valid(raise_exception=True)
        order = order_serializer.save()

        # Step 2: Create Order Items
        order_items = []
        for item_data in order_items_data:
            # Step 2.1: Check if external lens data exists in order item
            external_lens_data = item_data.get('external_lens_data')  # Assume request includes `external_lens_data`
            if external_lens_data:
                # Create the External Lens
                lens_data = external_lens_data.get('lens')
                powers_data = external_lens_data.get('powers', [])

                               # ✅ Validate ExternalLens data first
                if not lens_data:
                    raise ValidationError({'external_lens_data': 'Lens data is required for external lenses.'})

                # ✅ Create External Lens and assign ID
                created_lens = ExternalLensService.create_external_lens(lens_data, powers_data)
                item_data['external_lens'] = created_lens['external_lens']['id']


            item_data['order'] = order.id  # Attach the created order
            order_item_serializer = OrderItemSerializer(data=item_data)
            order_item_serializer.is_valid(raise_exception=True)
            order_items.append(order_item_serializer.save())  # Save and store items

        return order  # Return the created order instance
    
    @staticmethod
    @transaction.atomic
    def update_order(order, order_data, order_items_data, payments_data):
        """
        Updates an order along with its items and payments, including inline stock adjustments.
        No external stock validation service used — all logic handled here.
        """
        try:
            branch_id = order.branch_id
            if not branch_id:
                raise ValueError("Order is not associated with a branch.")

            # ✅ Step 1: Capture current items for comparison
            existing_items = {item.id: item for item in order.order_items.all()}

            # ✅ Step 2: Update order fields
            order.sub_total = order_data.get('sub_total', order.sub_total)
            order.discount = order_data.get('discount', order.discount)
            order.total_price = order_data.get('total_price', order.total_price)
            order.status = order_data.get('status', order.status)
            order.sales_staff_code_id = order_data.get('sales_staff_code', order.sales_staff_code_id)
            order.order_remark = order_data.get('order_remark', order.order_remark)
            order.save()

            # ✅ Step 3: Loop through incoming items
            for item_data in order_items_data:
                item_id = item_data.get('id')
                is_non_stock = item_data.get('is_non_stock', False)
                quantity = item_data['quantity']

                # External lens creation/update
                external_lens_data = item_data.get('external_lens_data')
                if external_lens_data:
                    lens_data = external_lens_data.get("lens")
                    powers_data = external_lens_data.get("powers", [])

                    if not lens_data:
                        raise ValidationError({"external_lens_data": "Lens data is required."})

                    if item_data.get("external_lens"):
                        existing_lens = ExternalLens.objects.get(id=item_data["external_lens"])
                        lens_serializer = ExternalLensSerializer(existing_lens, data=lens_data, partial=True)
                        lens_serializer.is_valid(raise_exception=True)
                        lens_serializer.save()
                    else:
                        created_lens = ExternalLensService.create_external_lens(lens_data, powers_data)
                        item_data["external_lens"] = created_lens["external_lens"]["id"]

                # 🛠️ Handle stock deduction
                if not is_non_stock:
                    stock = None
                    stock_type = None

                    if item_data.get("lens"):
                        stock = LensStock.objects.select_for_update().filter(lens_id=item_data["lens"], branch_id=branch_id).first()
                        stock_type = "lens"
                    elif item_data.get("frame"):
                        stock = FrameStock.objects.select_for_update().filter(frame_id=item_data["frame"], branch_id=branch_id).first()
                        stock_type = "frame"
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
                            stock.save()
                    else:
                        if stock.qty < quantity:
                            raise ValueError(f"Insufficient {stock_type} stock.")
                        stock.qty -= quantity
                        stock.save()

                # ✅ Update or Create order item
                if item_id and item_id in existing_items:
                    existing_item = existing_items.pop(item_id)
                    existing_item.quantity = quantity
                    existing_item.price_per_unit = item_data['price_per_unit']
                    existing_item.subtotal = item_data['subtotal']
                    existing_item.external_lens_id = item_data.get("external_lens", existing_item.external_lens_id)
                    existing_item.lens_id = item_data.get("lens", existing_item.lens_id)
                    existing_item.frame_id = item_data.get("frame", existing_item.frame_id)
                    existing_item.lens_cleaner_id = item_data.get("lens_cleaner", existing_item.lens_cleaner_id)
                    existing_item.save()
                else:
                    OrderItem.objects.create(
                        order=order,
                        quantity=quantity,
                        price_per_unit=item_data['price_per_unit'],
                        subtotal=item_data['subtotal'],
                        external_lens_id=item_data.get("external_lens"),
                        lens_id=item_data.get("lens"),
                        frame_id=item_data.get("frame"),
                        lens_cleaner_id=item_data.get("lens_cleaner")
                    )

            # ✅ Step 4: Restock and delete removed items
            for deleted_item in existing_items.values():
                if not deleted_item.is_non_stock:
                    stock = None
                    if deleted_item.lens_id:
                        stock = LensStock.objects.filter(lens_id=deleted_item.lens_id, branch_id=branch_id).first()
                    elif deleted_item.frame_id:
                        stock = FrameStock.objects.filter(frame_id=deleted_item.frame_id, branch_id=branch_id).first()
                    elif deleted_item.lens_cleaner_id:
                        stock = LensCleanerStock.objects.filter(lens_cleaner_id=deleted_item.lens_cleaner_id, branch_id=branch_id).first()

                    if stock:
                        stock.qty += deleted_item.quantity
                        stock.save()

                deleted_item.delete()

            # ✅ Step 5: Update Payments
            total_payment = OrderPaymentService.update_process_payments(order, payments_data)
            if total_payment > order.total_price:
                raise ValueError("Total payments exceed the order total price.")

            return order

        except ExternalLens.DoesNotExist:
            raise ValueError("Invalid External Lens ID.")
        except Exception as e:
            transaction.set_rollback(True)
            raise ValueError(f"Order update failed: {str(e)}")
