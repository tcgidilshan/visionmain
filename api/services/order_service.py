from ..models import Order, OrderItem, LensStock, LensCleanerStock, FrameStock,Lens,LensCleaner,Frame
from ..serializers import OrderSerializer, OrderItemSerializer
from django.db import transaction
from ..services.order_payment_service import OrderPaymentService


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

            # ✅ Step 2: Update Order Items & Adjust Stock
            existing_items = {item.id: item for item in order.order_items.all()}  # Get current items

            for item_data in order_items_data:
                item_id = item_data.get('id')

                # ✅ Fetch instances for ForeignKey fields
                lens_instance = Lens.objects.get(id=item_data['lens']) if 'lens' in item_data else None
                frame_instance = Frame.objects.get(id=item_data['frame']) if 'frame' in item_data else None
                cleaner_instance = LensCleaner.objects.get(id=item_data['lens_cleaner']) if 'lens_cleaner' in item_data else None

                if item_id and item_id in existing_items:
                    # ✅ Update Existing Item
                    existing_item = existing_items.pop(item_id)
                    existing_item.quantity = item_data['quantity']
                    existing_item.price_per_unit = item_data['price_per_unit']
                    existing_item.subtotal = item_data['subtotal']

                    # ✅ Assign ForeignKey instances properly
                    existing_item.lens = lens_instance
                    existing_item.frame = frame_instance
                    existing_item.lens_cleaner = cleaner_instance

                    existing_item.save()

                else:
                    # ✅ Add New Item (Validate Stock First)
                    stock_item = OrderService.validate_and_get_stock(item_data)
                    if stock_item.qty < item_data['quantity']:
                        raise ValueError(f"Insufficient stock for item {item_data}")

                    new_item = OrderItem.objects.create(
                        order=order,
                        quantity=item_data['quantity'],
                        price_per_unit=item_data['price_per_unit'],
                        subtotal=item_data['subtotal'],
                        lens=lens_instance,
                        frame=frame_instance,
                        lens_cleaner=cleaner_instance
                    )
                    stock_item.qty -= item_data['quantity']
                    stock_item.save()

            # ✅ Step 3: Remove Deleted Items & Restore Stock
                for deleted_item in existing_items.values():
                    # ✅ Ensure OrderItem has an ID before deleting
                    if deleted_item.id:
                        stock_item = OrderService.validate_and_get_stock({
                            "lens": deleted_item.lens.id if deleted_item.lens else None,
                            "frame": deleted_item.frame.id if deleted_item.frame else None,
                            "lens_cleaner": deleted_item.lens_cleaner.id if deleted_item.lens_cleaner else None,
                        })
                        
                        stock_item.qty += deleted_item.quantity  # Restore stock
                        stock_item.save()
                        deleted_item.delete()  # ✅ Only delete if it exists in DB
                    else:
                        print(f"Skipping delete for OrderItem with no ID: {deleted_item}")



            # ✅ Step 4: Handle Payments
            total_payment = OrderPaymentService.process_payments(order, payments_data)

            # ✅ Step 5: Validate Payments (Ensure it doesn’t exceed total_price)
            if total_payment > order.total_price:
                raise ValueError("Total payments exceed the order total price.")

            return order  # ✅ Return the updated order

        except Lens.DoesNotExist:
            raise ValueError("Invalid Lens ID. Lens does not exist.")
        except Frame.DoesNotExist:
            raise ValueError("Invalid Frame ID. Frame does not exist.")
        except LensCleaner.DoesNotExist:
            raise ValueError("Invalid Lens Cleaner ID. Lens Cleaner does not exist.")
        except Exception as e:
            transaction.set_rollback(True)
            raise ValueError(f"Order update failed: {str(e)}")

    @staticmethod
    def validate_and_get_stock(item_data):
        """ Helper function to get stock based on item type and handle missing stocks properly """
        try:
            if 'lens' in item_data and item_data['lens']:
                lens_id = item_data['lens'].id if hasattr(item_data['lens'], 'id') else item_data['lens']
                return LensStock.objects.select_for_update().get(lens_id=lens_id)
            elif 'lens_cleaner' in item_data and item_data['lens_cleaner']:
                cleaner_id = item_data['lens_cleaner'].id if hasattr(item_data['lens_cleaner'], 'id') else item_data['lens_cleaner']
                return LensCleanerStock.objects.select_for_update().get(lens_cleaner_id=cleaner_id)
            elif 'frame' in item_data and item_data['frame']:
                frame_id = item_data['frame'].id if hasattr(item_data['frame'], 'id') else item_data['frame']
                return FrameStock.objects.select_for_update().get(frame_id=frame_id)
            else:
                raise ValueError("Invalid item type.")
        except LensStock.DoesNotExist:
            raise ValueError(f"LensStock not found for Lens ID {lens_id}.")
        except LensCleanerStock.DoesNotExist:
            raise ValueError(f"LensCleanerStock not found for Cleaner ID {cleaner_id}.")
        except FrameStock.DoesNotExist:
            raise ValueError(f"FrameStock not found for Frame ID {frame_id}.")


