# services/frame_only_order_service.py

from decimal import Decimal
from django.db import transaction
from ..models import Order, OrderItem, Invoice
from datetime import date

class FrameOnlyOrderService:

    @staticmethod
    @transaction.atomic
    def create(data):
        customer = data['customer']
        frame = data['frame']
        quantity = data['quantity']
        price_per_unit = data['price_per_unit']
        branch_id = data['branch_id']

        # sales_staff_code comes as CustomUser instance (serializer!)
        sales_staff_code = data.get('sales_staff_code', None)

        # Prepare item structure
        order_items_data = [{
            "frame": frame.id,
            "quantity": quantity,
            "is_non_stock": False
        }]

        # Validate stock
        stock_updates = FrameOnlyOrderService.validate_stocks(order_items_data, branch_id)

        # Calculate totals
        subtotal = Decimal(quantity) * price_per_unit
        total_price = subtotal

        # Create Order
        order = Order.objects.create(
            customer=customer,
            branch_id=branch_id,
            sales_staff_code=sales_staff_code,  # ✅ Pass the object directly
            refraction=None,
            is_frame_only=True,
            sub_total=subtotal,
            total_price=total_price,
            discount=Decimal('0.00'),
            status='pending',
            user_date=date.today()
        )

        # Create OrderItem
        OrderItem.objects.create(
            order=order,
            frame=frame,
            quantity=quantity,
            price_per_unit=price_per_unit,
            is_non_stock=False
        )

        # Adjust Stocks
        FrameOnlyOrderService.adjust_stocks(stock_updates)

        # Create Invoice
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
