# services/frame_only_order_service.py

from decimal import Decimal
from django.db import transaction
from ..models import Order, OrderItem, Invoice, Patient
from datetime import date
from django.db.models import Q

class FrameOnlyOrderService:

    @staticmethod
    @transaction.atomic
    def create(data):
        patient_data = data['patient']
        frame = data['frame']
        quantity = data['quantity']
        price_per_unit = data['price_per_unit']
        branch_id = data['branch_id']
        sales_staff_code = data.get('sales_staff_code', None)

        # 🧠 Step 1: Get or create patient
        phone = patient_data.get('phone_number')
        nic = patient_data.get('nic')

        existing_patient = Patient.objects.filter(
            phone_number=phone
        ).first()

        if existing_patient:
            customer = existing_patient
        else:
            customer = Patient.objects.create(**patient_data)

        # Step 2: Prepare item
        order_items_data = [{
            "frame": frame.id,
            "quantity": quantity,
            "is_non_stock": False
        }]

        # Step 3: Validate stock
        stock_updates = FrameOnlyOrderService.validate_stocks(order_items_data, branch_id)

        # Step 4: Totals
        subtotal = Decimal(quantity) * price_per_unit
        total_price = subtotal

        # Step 5: Create order
        order = Order.objects.create(
            customer=customer,
            branch_id=branch_id,
            sales_staff_code=sales_staff_code,
            refraction=None,
            is_frame_only=True,
            sub_total=subtotal,
            total_price=total_price,
            discount = Decimal(data.get("discount") or "0.00"),
            status = data.get("status", "pending"),
            user_date=date.today()
        )

        # Step 6: Order item
        OrderItem.objects.create(
            order=order,
            frame=frame,
            quantity=quantity,
            price_per_unit=price_per_unit,
            is_non_stock=False
        )

        # Step 7: Adjust stock
        FrameOnlyOrderService.adjust_stocks(stock_updates)

        # Step 8: Invoice
        Invoice.objects.create(
            order=order,
            invoice_type='factory'
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
