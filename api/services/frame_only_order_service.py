# services/frame_only_order_service.py

from decimal import Decimal
from django.db import transaction
from ..models import Order, OrderItem, Invoice, Patient, FrameStock,OrderProgress
from datetime import date
from django.db.models import Q
from ..services.patient_service import PatientService
class FrameOnlyOrderService:

    @staticmethod
    @transaction.atomic
    def create(data):

        patient_data = data.get("patient")
        frame = data["frame"]
        quantity = data["quantity"]
        price_per_unit = data["price_per_unit"]
        branch_id = data["branch_id"]
        sales_staff_code = data.get("sales_staff_code", None)
        
        

        # 🧠 Step 1: Get or create patient
        customer = None
        if patient_data:
            customer = PatientService.create_or_update_patient(patient_data)
        
        # Step 2: Prepare order item
        order_items_data = [{
            "frame": frame.id,
            "quantity": quantity,
            "is_non_stock": False
        }]

        # Step 3: Validate stock
        stock_updates = FrameOnlyOrderService.validate_stocks(order_items_data, branch_id)

        # Step 4: Totals
        subtotal = Decimal(quantity) * price_per_unit
        discount = Decimal(data.get("discount") or "0.00")
        total_price = subtotal - discount

        # Step 5: Create order
        order = Order.objects.create(
            customer=customer,
            branch_id=branch_id,
            sales_staff_code=sales_staff_code,
            refraction=None,
            is_frame_only=True,
            sub_total=subtotal,
            total_price=total_price,
            discount=discount,
            status=data.get("status", "pending"),
            user_date=date.today(),
            order_remark=data.get("order_remark", "")  # Add order_remark from payload
        )
        

        # 1. Update the progress_status field (capture previous if needed)
        incoming_status = data.get('progress_status', None)
        last_progress = order.order_progress_status.order_by('-changed_at').first()
        # Always log if this is the first status, or if it's different from the last logged status
        print(data)
    
        if incoming_status and (
            last_progress is None or last_progress.progress_status != incoming_status
        ):
            OrderProgress.objects.create(
                order=order,
                progress_status=incoming_status,
            )
            
        # Step 6: Create order item
        OrderItem.objects.create(
            order=order,
            frame=frame,
            quantity=quantity,
            price_per_unit=price_per_unit,
            is_non_stock=False,
            subtotal=subtotal
        )

        # Step 7: Adjust stock
        FrameOnlyOrderService.adjust_stocks(stock_updates)

        # Step 8: Create invoice
        Invoice.objects.create(
            order=order,
            invoice_type="factory"
        )

        return order

    @staticmethod
    def validate_stocks(order_items_data, branch_id):
        """
        Validates stock availability.
        """
        if not order_items_data:
            raise ValueError("Order items are required.")
        if not branch_id:
            raise ValueError("Branch ID is required.")

        stock_updates = []
        with transaction.atomic():
            for item_data in order_items_data:
                if item_data.get('is_non_stock'):
                    continue

                stock = None
                stock_type = None

                if item_data.get('frame'):
                    from ..models import FrameStock
                    stock = FrameStock.objects.select_for_update().filter(
                        frame_id=item_data['frame'], branch_id=branch_id
                    ).first()
                    stock_type = 'frame'

                if not stock or stock.qty < item_data['quantity']:
                    raise ValueError(
                        f"Insufficient stock for {stock_type} ID {item_data.get(stock_type)} in branch {branch_id}."
                    )

                stock_updates.append((stock_type, stock, item_data['quantity']))
        return stock_updates

    @staticmethod
    def adjust_stocks(stock_updates):
        """
        Deducts stock quantities.
        """
        with transaction.atomic():
            for stock_type, stock, quantity in stock_updates:
                stock.qty -= quantity
                stock.save()

    @staticmethod
    @transaction.atomic
    def update(order, data):
        # 🔹 Step 1: Update or create patient
        patient_data = data.get("patient")
        if patient_data:
            customer = PatientService.create_or_update_patient(patient_data)
            order.customer = customer

        # 🔹 Step 2: Detect changes
        new_frame = data["frame"]
        new_quantity = data["quantity"]
        price_per_unit = data["price_per_unit"]
        branch_id = data["branch_id"]

        existing_item = order.order_items.first()
        old_frame = existing_item.frame if existing_item else None
        old_quantity = existing_item.quantity if existing_item else 0

        frame_changed = not old_frame or old_frame.id != new_frame.id
        qty_increased = new_quantity > old_quantity

        # 🔁 Step 3: Restock if frame changed or quantity reduced
        if old_frame and (frame_changed or new_quantity < old_quantity):
            restock_qty = old_quantity if frame_changed else (old_quantity - new_quantity)
            stock = FrameStock.objects.select_for_update().filter(
                frame_id=old_frame.id,
                branch_id=branch_id
            ).first()
            if stock:
                stock.qty += restock_qty
                stock.save()

        # 🔐 Step 4: Validate and deduct stock if needed
        if frame_changed or qty_increased:
            order_items_data = [{
                "frame": new_frame.id,
                "quantity": new_quantity,
                "is_non_stock": False
            }]
            stock_updates = FrameOnlyOrderService.validate_stocks(order_items_data, branch_id)
            FrameOnlyOrderService.adjust_stocks(stock_updates)

        # 🔹 Step 5: Update order fields
        subtotal = Decimal(new_quantity) * price_per_unit
        discount = Decimal(data.get("discount") or "0.00")
        total_price = subtotal - discount

        order.branch_id = branch_id
        order.sales_staff_code_id = data.get("sales_staff_code", order.sales_staff_code_id)
        order.sub_total = subtotal
        order.discount = discount
        order.total_price = total_price
        order.status = data.get("status", order.status)
        order.progress_status = data.get("progress_status", order.progress_status)
        order.save()

        # 🔹 Step 6: Replace order item
        if existing_item:
            existing_item.delete()

        OrderItem.objects.create(
            order=order,
            frame=new_frame,
            quantity=new_quantity,
            price_per_unit=price_per_unit,
            is_non_stock=False,
            subtotal=subtotal
        )

        return order
