from ..models import Order, OrderItem, LensStock, LensCleanerStock, FrameStock,Lens,LensCleaner,Frame,ExternalLens
from ..serializers import OrderSerializer, OrderItemSerializer, ExternalLensSerializer
from django.db import transaction
from ..services.order_payment_service import OrderPaymentService
from ..services.external_lens_service import ExternalLensService
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

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
        Updates an existing order along with its items and payments.
        Ensures stock validation and payment updates.
        """
        try:
            # ✅ Step 1: Update Order Details
            order.sub_total = order_data.get('sub_total', order.sub_total)
            order.discount = order_data.get('discount', order.discount)
            order.total_price = order_data.get('total_price', order.total_price)
            order.status = order_data.get('status', order.status)
            order.sales_staff_code_id = order_data.get('sales_staff_code', order.sales_staff_code_id)
            order.remark = order_data.get('remark', order.remark)
            order.save()  # ✅ Save updated order

            # ✅ Step 2: Update Order Items & External Lenses
            existing_items = {item.id: item for item in order.order_items.all()}  # Get current items

            for item_data in order_items_data:
                item_id = item_data.get('id')

                # ✅ Handle External Lens Data
                external_lens_data = item_data.get('external_lens_data', None)

                if external_lens_data:
                    lens_data = external_lens_data.get("lens", None)
                    powers_data = external_lens_data.get("powers", [])

                    if not lens_data:
                        raise ValidationError({"external_lens_data": "Lens data is required for external lenses."})

                    # ✅ If `external_lens` exists in order item, update it
                    if item_data.get("external_lens"):
                        existing_lens = ExternalLens.objects.get(id=item_data["external_lens"])
                        lens_serializer = ExternalLensSerializer(existing_lens, data=lens_data, partial=True)

                        if lens_serializer.is_valid():
                            lens_serializer.save()
                            print(f"✅ Updated External Lens: {existing_lens.id}")
                        else:
                            raise ValidationError(lens_serializer.errors)

                    else:
                        # ✅ Otherwise, create a new external lens
                        created_lens = ExternalLensService.create_external_lens(lens_data, powers_data)
                        item_data["external_lens"] = created_lens["external_lens"]["id"]
                        print(f"✅ Created New External Lens: {created_lens['external_lens']['id']}")

                if item_id and item_id in existing_items:
                    # ✅ Update Existing Order Item
                    existing_item = existing_items.pop(item_id)
                    existing_item.quantity = item_data['quantity']
                    existing_item.price_per_unit = item_data['price_per_unit']
                    existing_item.subtotal = item_data['subtotal']

                    # ✅ Assign External Lens if Updated
                    if "external_lens" in item_data:
                        existing_item.external_lens_id = item_data["external_lens"]

                    existing_item.save()

                else:
                    # ✅ Add New Order Item
                    new_item = OrderItem.objects.create(
                        order=order,
                        quantity=item_data['quantity'],
                        price_per_unit=item_data['price_per_unit'],
                        subtotal=item_data['subtotal'],
                        external_lens_id=item_data.get("external_lens")
                    )

            # ✅ Step 3: Remove Deleted Items
            for deleted_item in existing_items.values():
                deleted_item.delete()

            # ✅ Step 4: Handle Payments
            total_payment = OrderPaymentService.update_process_payments(order, payments_data)

            # ✅ Step 5: Validate Payments (Ensure it doesn’t exceed total_price)
            if total_payment > order.total_price:
                raise ValueError("Total payments exceed the order total price.")

            return order  # ✅ Return the updated order

        except ExternalLens.DoesNotExist:
            raise ValueError("Invalid External Lens ID. External Lens does not exist.")
        except Exception as e:
            transaction.set_rollback(True)
            raise ValueError(f"Order update failed: {str(e)}")
