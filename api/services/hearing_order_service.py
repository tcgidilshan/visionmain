from decimal import Decimal
from django.db import transaction
from ..models import Order, OrderItem, Invoice, Patient, HearingItemStock, OrderProgress
from datetime import date
from ..services.patient_service import PatientService

class HearingOrderService:
    """
    Service class for handling hearing item orders with similar functionality to FrameOnlyOrderService.
    """

    @staticmethod
    @transaction.atomic
    def create(data):
        """
        Creates a new hearing item order with the provided data.
        """
        patient_data = data.get("patient")
        hearing_item = data["hearing_item"]
        quantity = data["quantity"]
        price_per_unit = data["price_per_unit"]
        branch_id = data["branch_id"]
        sales_staff_code = data.get("sales_staff_code")
        serial_no = data.get("serial_no")
        battery = data.get("battery")

        # Get or create patient
        customer = None
        if patient_data:
            customer = PatientService.create_or_update_patient(patient_data)
        
        # Prepare order item data
        order_items_data = [{
            "hearing_item": hearing_item.id,
            "quantity": quantity,
            "is_non_stock": False,
            "serial_no": serial_no,
            "battery": battery
        }]

        # Validate stock
        stock_updates = HearingOrderService.validate_stocks(order_items_data, branch_id)

        # Calculate totals
        subtotal = Decimal(quantity) * price_per_unit
        discount = Decimal(data.get("discount") or "0.00")
        total_price = subtotal - discount

        # Create order
        order = Order.objects.create(
            customer=customer,
            branch_id=branch_id,
            sales_staff_code=sales_staff_code,
            refraction=None,
            sub_total=subtotal,
            total_price=total_price,
            discount=discount,
            status=data.get("status", "pending"),
            user_date=date.today(),
            order_remark=data.get("order_remark", "")
        )

        # Create order item
        OrderItem.objects.create(
            order=order,
            hearing_item=hearing_item,
            quantity=quantity,
            price_per_unit=price_per_unit,
            is_non_stock=False,
            subtotal=subtotal,
            serial_no=serial_no,
            battery=battery
        )

        # Adjust stock
        HearingOrderService.adjust_stocks(stock_updates)

        # Create invoice
        Invoice.objects.create(
            order=order,
            invoice_type="hearing"  # Or appropriate invoice type
        )

        return order

    @staticmethod
    def validate_stocks(order_items_data, branch_id):
        """
        Validates stock availability for hearing items.
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
                if item_data.get('hearing_item'):
                    stock = HearingItemStock.objects.select_for_update().filter(
                        hearing_item_id=item_data['hearing_item'],
                        branch_id=branch_id
                    ).first()

                if not stock or stock.qty < item_data['quantity']:
                    raise ValueError(
                        f"Insufficient stock for hearing item ID {item_data.get('hearing_item')} "
                        f"in branch {branch_id}."
                    )

                stock_updates.append(('hearing_item', stock, item_data['quantity']))
        return stock_updates

    @staticmethod
    def adjust_stocks(stock_updates):
        """
        Deducts stock quantities for hearing items.
        """
        with transaction.atomic():
            for stock_type, stock, quantity in stock_updates:
                stock.qty -= quantity
                stock.save()

    @staticmethod
    @transaction.atomic
    def update(order, data):
        """
        Updates an existing hearing item order.
        """
        # Update or create patient
        patient_data = data.get("patient")
        if patient_data:
            customer = PatientService.create_or_update_patient(patient_data)
            order.customer = customer

        # Get order data
        new_hearing_item = data["hearing_item"]
        new_quantity = data["quantity"]
        price_per_unit = data["price_per_unit"]
        branch_id = data["branch_id"]
        serial_no = data.get("serial_no")
        battery = data.get("battery")

        # Get existing item
        existing_item = order.order_items.first()
        old_hearing_item = existing_item.hearing_item if existing_item else None
        old_quantity = existing_item.quantity if existing_item else 0

        item_changed = not old_hearing_item or old_hearing_item.id != new_hearing_item.id
        qty_increased = new_quantity > old_quantity

        # Restock if item changed or quantity reduced
        if old_hearing_item and (item_changed or new_quantity < old_quantity):
            restock_qty = old_quantity if item_changed else (old_quantity - new_quantity)
            stock = HearingItemStock.objects.select_for_update().filter(
                hearing_item_id=old_hearing_item.id,
                branch_id=branch_id
            ).first()
            if stock:
                stock.qty += restock_qty
                stock.save()

        # Validate and deduct stock if needed
        if item_changed or qty_increased:
            order_items_data = [{
                "hearing_item": new_hearing_item.id,
                "quantity": new_quantity,
                "is_non_stock": False
            }]
            stock_updates = HearingOrderService.validate_stocks(order_items_data, branch_id)
            HearingOrderService.adjust_stocks(stock_updates)

        # Update order fields
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

        # Update or replace order item
        if existing_item:
            existing_item.delete()

        OrderItem.objects.create(
            order=order,
            hearing_item=new_hearing_item,
            quantity=new_quantity,
            price_per_unit=price_per_unit,
            is_non_stock=False,
            subtotal=subtotal,
            serial_no=serial_no,
            battery=battery
        )

        return order