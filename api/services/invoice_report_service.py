from datetime import datetime, time
from django.db.models import Sum, Q
from api.models import Invoice, Order, OrderPayment,Appointment, ChannelPayment, SolderingPayment, SolderingOrder,SolderingInvoice, PaymentMethodBanks, Expense
from django.utils import timezone
from api.services.time_zone_convert_service import TimezoneConverterService
from django.db.models.functions import TruncDate

class InvoiceReportService:

    @staticmethod
    def get_invoice_report_by_payment_date(payment_date_str, branch_id):
        """
        Returns filtered invoice data (factory & normal) based on payment date and branch.
        """
        # print(f"\n=== DEBUG: get_invoice_report_by_payment_date ===")
        # print(f"Input - payment_date_str: {payment_date_str}, branch_id: {branch_id}")

        try:
            payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
            # print(f"Parsed payment_date: {payment_date}")
        except ValueError as e:
            error_msg = f"Error parsing date {payment_date_str}: {str(e)}"
            # print(error_msg)
            raise ValueError("Invalid payment date format. Use YYYY-MM-DD.")

        # Get all payments made on that date for that branch
        # print(f"Querying OrderPayment for date: {payment_date}, branch_id: {branch_id}")
        
        # Using range to handle timezone issues
        start_datetime = timezone.make_aware(
            datetime.combine(payment_date, time.min)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(payment_date, time.max)
        )
        
    # print(f"Date range for query: {start_datetime} to {end_datetime}")
        
        payments = OrderPayment.all_objects.select_related("order").filter(
            (Q(payment_date__range=(start_datetime, end_datetime)) |  Q(order__deleted_at__range=(start_datetime, end_datetime))),
            order__branch_id=branch_id,
            is_edited=False
        )
        # print(f"Found {payments.count()} payments")

        # Get all active payment method banks for this branch (credit card banks only, to match frontend)
        branch_banks = PaymentMethodBanks.objects.filter(
            branch_id=branch_id,
            payment_method='credit_card',
            is_active=True
        ).values_list('name', flat=True)
        
        # Organize payments by order
        # print("\n=== Processing Payments ===")
        payments_by_order = {}
        for payment in payments:
            oid = payment.order_id
            # print(f"\nProcessing payment ID: {payment.id} for order ID: {oid}")
            # print(f"Payment amount: {payment.amount}, method: {payment.payment_method}, date: {payment.payment_date}")
            
            if oid not in payments_by_order:
                payments_by_order[oid] = {
                    "cash": 0,
                    "credit_card": 0,
                    "online_transfer": 0,
                    "total": 0
                }
                # Initialize all branch banks with 0
                for bank_name in branch_banks:
                    payments_by_order[oid][bank_name] = 0

            payments_by_order[oid][payment.payment_method] += float(payment.amount)
            payments_by_order[oid]["total"] += float(payment.amount)
            
            # Add bank total if payment has a bank
            if payment.payment_method_bank:
                bank_name = payment.payment_method_bank.name
                payments_by_order[oid][bank_name] += float(payment.amount)

        # Debug: Print the payments_by_order keys (order IDs)
        # print(f"\nOrders with payments: {list(payments_by_order.keys())}")
        
        # Get all invoices where related order has at least 1 payment on that date
        invoice_qs = Invoice.all_objects.select_related("order").filter(
            Q(order_id__in=payments_by_order.keys()) |
            Q(invoice_date__range=(start_datetime, end_datetime))
        ).filter(
            order__branch_id=branch_id,
            # order__is_refund=False
            # is_deleted=False,
            # order__is_deleted=False
        )
        
        # for i in invoice_qs:
        #     print(f"invoice_id={i.id}, invoice_number={i.invoice_number}, invoice_date={i.invoice_date}, order_id={i.order_id}, order_is_deleted={i.order.is_deleted}")

        results = []

        for invoice in invoice_qs:
            order_id = invoice.order_id
            payment_data = payments_by_order.get(order_id, {})
            
            # Use order.total_payment which accounts for refund expenses
            # total_payment = sum(OrderPayments) - sum(Expenses)
            total_payment = float(invoice.order.total_payment or 0)
          
            data = {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_type": invoice.invoice_type,
                "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d"),
                "order_id": order_id,
                "total_invoice_price": float(invoice.order.total_price),
                "total_cash_payment": payment_data.get("cash", 0),
                "total_credit_card_payment": payment_data.get("credit_card", 0),
                "total_online_payment": payment_data.get("online_transfer", 0),
                "total_payment": total_payment,
                "balance": float(invoice.order.total_price) - total_payment,
                "is_deleted": invoice.is_deleted,
                "is_refund": invoice.order.is_refund
            }

            # Add bank totals as separate keys
            for key, value in payment_data.items():
                if key not in ["cash", "credit_card", "online_transfer", "total"]:
                    data[key] = value

            results.append(data)

        # Debug output for the report data
        # print("\n=== Final Report Data ===")
        # print(f"Number of orders in report: {len(results)}")
        # if results:
        #     print("Sample order data:")
        #     for i, order in enumerate(results[:3]):  # Print first 3 orders or fewer
        #         print(f"Order {i+1}: {order}")
        # else:
        #     print("No orders found in report data")
            
        #     # Debug: Check if there are any payments at all in the system
        #     total_payments = OrderPayment.objects.count()
        #     print(f"\nDebug: Total payments in system: {total_payments}")
        #     if total_payments > 0:
        #         latest_payment = OrderPayment.objects.order_by('-payment_date').first()
        #         print(f"Latest payment in system: ID={latest_payment.id}, Date={latest_payment.payment_date}, Amount={latest_payment.amount}")
        # ===== PROCESS SOLDERING ORDERS =====
    # Get all soldering payments made on that date for that branch
        soldering_payments = SolderingPayment.objects.select_related("order").filter(
            payment_date__range=(start_datetime, end_datetime),
            order__branch_id=branch_id,
            is_deleted=False
        )
        # print(f"Found {soldering_payments.count()} soldering payments")

        # Organize soldering payments by order
        soldering_payments_by_order = {}
        for payment in soldering_payments:
            oid = payment.order_id
            if oid not in soldering_payments_by_order:
                soldering_payments_by_order[oid] = {
                    "cash": 0,
                    "credit_card": 0,
                    "online_transfer": 0,
                    "total": 0
                }
                # Initialize all branch banks with 0
                for bank_name in branch_banks:
                    soldering_payments_by_order[oid][bank_name] = 0

            soldering_payments_by_order[oid][payment.payment_method] += float(payment.amount)
            soldering_payments_by_order[oid]["total"] += float(payment.amount)
            
            # Add bank total if payment has a bank
            if payment.payment_method_bank:
                bank_name = payment.payment_method_bank.name
                soldering_payments_by_order[oid][bank_name] += float(payment.amount)

        # Get all soldering invoices where related order has at least 1 payment on that date
        soldering_invoice_qs = SolderingInvoice.objects.select_related("order").filter(
            order_id__in=soldering_payments_by_order.keys(),
            order__branch_id=branch_id,
            is_deleted=False,
            order__is_deleted=False
        )
        
        # print(f"Found {soldering_invoice_qs.count()} soldering invoices")

        for invoice in soldering_invoice_qs:
            order_id = invoice.order_id
            payment_data = soldering_payments_by_order.get(order_id, {})
            
            # Use order.total_payment which accounts for refund expenses (if applicable to soldering)
            # total_payment = sum(SolderingPayments) - sum(Expenses)
            # Note: SolderingOrder might not have total_payment field, fallback to payment_data total
            total_payment = float(getattr(invoice.order, 'total_payment', None) or payment_data.get("total", 0))
            
            data = {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_type": "soldering",  # Mark as soldering type
                "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d"),
                "order_id": order_id,
                "total_invoice_price": float(invoice.order.price),  # Use price from SolderingOrder
                "total_cash_payment": payment_data.get("cash", 0),
                "total_credit_card_payment": payment_data.get("credit_card", 0),
                "total_online_payment": payment_data.get("online_transfer", 0),
                "total_payment": total_payment,
                "balance": float(invoice.order.price) - total_payment
            }

            # Add bank totals as separate keys
            for key, value in payment_data.items():
                if key not in ["cash", "credit_card", "online_transfer", "total"]:
                    data[key] = value

            results.append(data)
        return results
    
    @staticmethod
    def get_factory_order_report(start_date_str, end_date_str, branch_id, filter_type='all'):
        """
        Generate a detailed factory order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            filter_type (str): Type of filtering - 'payment_date', 'invoice_date', or 'all'
            
        Returns:
            dict: {
                'orders': [
                    {
                        'refraction_number': str,
                        'invoice_number': str,
                        'date': str (YYYY-MM-DD),
                        'time': str (HH:MM:SS),
                        'customer_name': str,
                        'nic': str,
                        'address': str,
                        'mobile_number': str,
                        'total_amount': float,
                        'paid_amount': float,
                        'balance': float,
                        'bill': float  # Same as total_amount for backward compatibility
                    },
                    ...
                ],
                'summary': {
                    'total_invoice_amount': float,
                    'total_paid_amount': float,
                    'total_balance': float
                }
            }
        """
        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date_str, end_date_str)
            
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_datetime > end_datetime:
            raise ValueError("Start date cannot be after end date.")
        
        # Get invoices based on filter type
        if filter_type == 'invoice_date':
            # Changed from OR logic to AND logic: only normal invoices that meet ALL conditions
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer',
            ).filter(
                Q(invoice_type='factory', invoice_date__range=(start_datetime, end_datetime))|
                 Q(invoice_type='factory', invoice_date__range=(start_datetime, end_datetime), order__deleted_at__range=(start_datetime, end_datetime))|
                 Q(invoice_type='factory', invoice_date__range=(start_datetime, end_datetime),order__refunded_at__range=(start_datetime, end_datetime)),
                # is_deleted=False,
                # order__is_deleted=False
            ).order_by('invoice_date')
            print(f"Factory invoices found by invoice_date: {invoices}")
        elif filter_type == 'payment_date':
            # Filter by payment date OR orders refunded/deleted in date range
            payments = OrderPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                order__branch_id=branch_id
            ).select_related('order')
            
            payment_order_ids = payments.values_list('order_id', flat=True).distinct()
            
            # Also get orders that were refunded or deleted in this date range
            refunded_deleted_orders = Order.all_objects.filter(
                Q(expense_refunds__is_refund=True, expense_refunds__created_at__range=(start_datetime, end_datetime)) | 
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            all_order_ids = set(payment_order_ids) | set(refunded_deleted_orders)
            
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer', 'order__refraction'
            ).filter(
                order_id__in=all_order_ids,
                invoice_type='factory',
                order__branch_id=branch_id,
                # is_deleted=False,
                # order__is_deleted=False
            ).order_by('invoice_date')
        elif filter_type == 'all':
            # Intersection logic: invoices with payments in date range AND created in date range
            # PLUS orders that were refunded/deleted in date range
            payments = OrderPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                order__branch_id=branch_id,
                order__invoice__invoice_type='factory'
            ).select_related('order')
            
            payment_order_ids = payments.values_list('order_id', flat=True).distinct()
            
            # Get orders that were refunded or deleted in this date range
            refunded_deleted_orders = Order.all_objects.filter(
                Q(expense_refunds__is_refund=True, expense_refunds__created_at__range=(start_datetime, end_datetime)) | 
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            # Combine payment orders and refunded/deleted orders
            all_order_ids = set(payment_order_ids) | set(refunded_deleted_orders)
            
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer', 'order__refraction'
            ).filter(
                Q(invoice_type='factory', invoice_date__range=(start_datetime, end_datetime))|
                 Q(invoice_type='factory',  order__deleted_at__range=(start_datetime, end_datetime))|
                 Q(invoice_type='factory', order__refunded_at__range=(start_datetime, end_datetime)),
                order__branch_id=branch_id,
                # is_deleted=False,
                # order__is_deleted=False
            ).distinct().order_by('invoice_date')
        else:
            raise ValueError("Invalid filter_type. Must be 'payment_date', 'invoice_date', or 'all'")
        
        # Get all payments for these orders
        order_ids = invoices.values_list('order_id', flat=True)
        payments = OrderPayment.objects.filter(
            order_id__in=order_ids
        ).values('order_id').annotate(
            total_paid=Sum('amount')
        )
        
        # Create a dictionary of order_id to total_paid
        payments_dict = {p['order_id']: float(p['total_paid'] or 0) for p in payments}
        
        # Prepare the report data
        orders = []
        total_invoice_amount = 0
        total_paid_amount = 0
        total_balance = 0
        total_refund_paid_amount = 0
        total_refund_balance = 0
        total_invoice_count = 0 
        # provided date range sum of expence order refunds 
        refund_amount = Expense.objects.filter(
            created_at__range=(start_datetime, end_datetime),
            order_refund__isnull=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        total_refund_paid_amount += float(refund_amount)
        print(f"Refund amount in date range: {refund_amount}")
        for invoice in invoices:
            order = invoice.order
            customer = order.customer
    
            
            # Get customer details from refraction if available, otherwise from patient
            
            # refraction_number = refraction. or ''
            customer_name = customer.name
            nic = customer.nic or ''
            address = customer.address or ''
            mobile_number = customer.phone_number or ''
            
            # Calculate payment totals
            total_amount = float(order.total_price)
            
            
            paid_amount = float(order.total_payment)
            
            balance = total_amount - paid_amount
            
            # Check if refund or deleted
            is_refund_or_deleted = order.is_refund or invoice.is_deleted or order.is_deleted
            
            if is_refund_or_deleted:
                total_refund_paid_amount += paid_amount
                total_refund_balance += balance
            else:
                total_invoice_amount += total_amount
                total_paid_amount += paid_amount
                total_balance += balance
                total_invoice_count += 1
            
            # Add order to results
            orders.append({
                # 'refraction_number': refraction_number,
                'invoice_number': invoice.invoice_number or '',
                'date': invoice.invoice_date.strftime("%Y-%m-%d"),
                'time': invoice.invoice_date.strftime("%H:%M:%S"),
                'customer_name': customer_name,
                'nic': nic or '',
                'address': address or '',
                'mobile_number': mobile_number or '',
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'balance': balance,
                'bill': total_amount,  # For backward compatibility
                'is_refund': order.is_refund,
                'is_deleted': invoice.is_deleted or order.is_deleted
            })
        
        return {
            'orders': orders,
            'summary': {
                'total_invoice_count': total_invoice_count, 
                'total_invoice_amount': total_invoice_amount,
                'total_paid_amount': total_paid_amount,
                'total_balance': total_balance,
                'total_refund_paid_amount': total_refund_paid_amount,
                'total_refund_balance': total_refund_balance
            }
        }
        #desing how you need refudn ,delete handle 
    @staticmethod
    def get_normal_order_report(start_date_str, end_date_str, branch_id, filter_type='all'):
        """
        Generate a detailed normal order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            filter_type (str): Type of filtering - 'payment_date', 'invoice_date', or 'all'
            
        Returns:
            dict: {
                'orders': [
                    {
                        'refraction_number': str,
                        'invoice_number': str,
                        'date': str (YYYY-MM-DD),
                        'time': str (HH:MM:SS),
                        'customer_name': str,
                        'nic': str,
                        'address': str,
                        'mobile_number': str,
                        'total_amount': float,
                        'paid_amount': float,
                        'balance': float,
                        'bill': float
                    },
                    ...
                ],
                'summary': {
                    'total_invoice_count': int,
                    'total_invoice_amount': float,
                    'total_paid_amount': float,
                    'total_balance': float,
                    'total_refund_paid_amount': float,
                    'total_refund_balance': float
                }
            }
        """
        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date_str, end_date_str)
            
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_datetime > end_datetime:
            raise ValueError("Start date cannot be after end date.")
        
        # Get invoices based on filter type
        if filter_type == 'invoice_date':
            # Changed from OR logic to AND logic: only normal invoices that meet ALL conditions
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer',
            ).filter(
                Q(invoice_type='normal', invoice_date__range=(start_datetime, end_datetime))|
                 Q(invoice_type='normal', invoice_date__range=(start_datetime, end_datetime), order__deleted_at__range=(start_datetime, end_datetime))|
                 Q(invoice_type='normal', invoice_date__range=(start_datetime, end_datetime),order__refunded_at__range=(start_datetime, end_datetime)),
                # is_deleted=False,
                # order__is_deleted=False
            ).order_by('invoice_date')
            print(f"Normal invoices found by invoice_date: {invoices}")
        elif filter_type == 'payment_date':
            # Filter by payment date OR orders refunded/deleted in date range
            payments = OrderPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                order__branch_id=branch_id
            ).select_related('order')
            
            payment_order_ids = payments.values_list('order_id', flat=True).distinct()
            
            # Also get orders that were refunded or deleted in this date range
            refunded_deleted_orders = Order.all_objects.filter(
                Q(expense_refunds__is_refund=True, expense_refunds__created_at__range=(start_datetime, end_datetime)) | 
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            all_order_ids = set(payment_order_ids) | set(refunded_deleted_orders)
            
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer', 'order__refraction'
            ).filter(
                order_id__in=all_order_ids,
                invoice_type='normal',
                order__branch_id=branch_id,
                # is_deleted=False,
                # order__is_deleted=False
            ).order_by('invoice_date')
        elif filter_type == 'all':
            # Intersection logic: invoices with payments in date range AND created in date range
            # PLUS orders that were refunded/deleted in date range
            payments = OrderPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                order__branch_id=branch_id,
                order__invoice__invoice_type='normal'
            ).select_related('order')
            
            payment_order_ids = payments.values_list('order_id', flat=True).distinct()
            
            # Get orders that were refunded or deleted in this date range
            refunded_deleted_orders = Order.all_objects.filter(
                Q(expense_refunds__is_refund=True, expense_refunds__created_at__range=(start_datetime, end_datetime)) | 
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            # Combine payment orders and refunded/deleted orders
            all_order_ids = set(payment_order_ids) | set(refunded_deleted_orders)
            
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer', 'order__refraction'
            ).filter(
                Q(invoice_type='normal', invoice_date__range=(start_datetime, end_datetime))|
                 Q(invoice_type='normal',  order__deleted_at__range=(start_datetime, end_datetime))|
                 Q(invoice_type='normal', order__refunded_at__range=(start_datetime, end_datetime)),
                order__branch_id=branch_id,
                # is_deleted=False,
                # order__is_deleted=False
            ).distinct().order_by('invoice_date')
        else:
            raise ValueError("Invalid filter_type. Must be 'payment_date', 'invoice_date', or 'all'")
        
        # Get all payments for these orders
        order_ids = invoices.values_list('order_id', flat=True)
        payments = OrderPayment.objects.filter(
            order_id__in=order_ids
        ).values('order_id').annotate(
            total_paid=Sum('amount')
        )
        
        # Create a dictionary of order_id to total_paid
        payments_dict = {p['order_id']: float(p['total_paid'] or 0) for p in payments}
        
        # Prepare the report data
        orders = []
        total_invoice_amount = 0
        total_paid_amount = 0
        total_balance = 0
        total_refund_paid_amount = 0
        total_refund_balance = 0
        total_invoice_count = 0 
        # provided date range sum of expence order refunds 
        refund_amount = Expense.objects.filter(
            created_at__range=(start_datetime, end_datetime),
            order_refund__isnull=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        total_refund_paid_amount += float(refund_amount)
        print(f"Refund amount in date range: {refund_amount}")
        for invoice in invoices:
            order = invoice.order
            customer = order.customer
    
            
            # Get customer details from refraction if available, otherwise from patient
            
            # refraction_number = refraction. or ''
            customer_name = customer.name
            nic = customer.nic or ''
            address = customer.address or ''
            mobile_number = customer.phone_number or ''
            
            # Calculate payment totals
            total_amount = float(order.total_price)
            
            
            paid_amount = float(order.total_payment)
            
            balance = total_amount - paid_amount
            
            # Check if refund or deleted
            is_refund_or_deleted = order.is_refund or invoice.is_deleted or order.is_deleted
            
            if is_refund_or_deleted:
                total_refund_paid_amount += paid_amount
                total_refund_balance += balance
            else:
                total_invoice_amount += total_amount
                total_paid_amount += paid_amount
                total_balance += balance
                total_invoice_count += 1
            
            # Add order to results
            orders.append({
                # 'refraction_number': refraction_number,
                'invoice_number': invoice.invoice_number or '',
                'date': invoice.invoice_date.strftime("%Y-%m-%d"),
                'time': invoice.invoice_date.strftime("%H:%M:%S"),
                'customer_name': customer_name,
                'nic': nic or '',
                'address': address or '',
                'mobile_number': mobile_number or '',
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'balance': balance,
                'bill': total_amount,  # For backward compatibility
                'is_refund': order.is_refund,
                'is_deleted': invoice.is_deleted or order.is_deleted
            })
        
        return {
            'orders': orders,
            'summary': {
                'total_invoice_count': total_invoice_count, 
                'total_invoice_amount': total_invoice_amount,
                'total_paid_amount': total_paid_amount,
                'total_balance': total_balance,
                'total_refund_paid_amount': total_refund_paid_amount,
                'total_refund_balance': total_refund_balance
            }
        }
        #desing how you need refudn ,delete handle

    @staticmethod
    def get_channel_order_report(start_date_str, end_date_str, branch_id, filter_type='all'):
        """
        Generate a detailed channel order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            filter_type (str): Type of filtering - 'payment_date', 'invoice_date', or 'all'
            
        Returns:
            dict: {
                'orders': [
                    {
                        'channel_id': int,
                        'channel_number': str,
                        'date': str (YYYY-MM-DD),
                        'time': str (HH:MM:SS),
                        'customer_name': str,
                        'address': str,
                        'mobile_number': str,
                        'total_amount': float,
                        'paid_amount': float,
                        'balance': float,
                        'bill': float  # Same as total_amount for consistency
                    },
                    ...
                ],
                'summary': {
                    'total_invoice_count': int,
                    'total_invoice_amount': float,
                    'total_paid_amount': float,
                    'total_balance': float,
                    'total_refund_paid_amount': float,
                    'total_refund_balance': float
                }
            }
        """
        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date_str, end_date_str)
            
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_datetime > end_datetime:
            raise ValueError("Start date cannot be after end date.")
        
        # Get appointments based on filter type
        if filter_type == 'invoice_date':
            # Only appointments created in date range OR deleted/refunded in date range
            appointments = Appointment.all_objects.select_related(
                'patient',
            ).filter(
                Q(created_at__range=(start_datetime, end_datetime))|
                Q(created_at__range=(start_datetime, end_datetime), deleted_at__range=(start_datetime, end_datetime))|
                Q(created_at__range=(start_datetime, end_datetime), refunded_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id,
                # is_deleted=False,
            ).order_by('created_at')
            print(f"Channel appointments found by invoice_date: {appointments}")
        elif filter_type == 'payment_date':
            # Filter by payment date OR appointments refunded/deleted in date range
            payments = ChannelPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                appointment__branch_id=branch_id
            ).select_related('appointment')
            
            payment_appointment_ids = payments.values_list('appointment_id', flat=True).distinct()
            
            # Also get appointments that were refunded or deleted in this date range
            refunded_deleted_appointments = Appointment.all_objects.filter(
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            all_appointment_ids = set(payment_appointment_ids) | set(refunded_deleted_appointments)
            
            appointments = Appointment.all_objects.select_related(
                'patient'
            ).filter(
                id__in=all_appointment_ids,
                branch_id=branch_id,
                # is_deleted=False,
            ).order_by('created_at')
        elif filter_type == 'all':
            # Intersection logic: appointments with payments in date range AND created in date range
            # PLUS appointments that were refunded/deleted in date range
            payments = ChannelPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                appointment__branch_id=branch_id
            ).select_related('appointment')
            
            payment_appointment_ids = payments.values_list('appointment_id', flat=True).distinct()
            
            # Get appointments that were refunded or deleted in this date range
            refunded_deleted_appointments = Appointment.all_objects.filter(
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            # Combine payment appointments and refunded/deleted appointments
            all_appointment_ids = set(payment_appointment_ids) | set(refunded_deleted_appointments)
            
            appointments = Appointment.all_objects.select_related(
                'patient'
            ).filter(
                Q(created_at__range=(start_datetime, end_datetime))|
                Q(deleted_at__range=(start_datetime, end_datetime))|
                Q(refunded_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id,
                # is_deleted=False,
            ).distinct().order_by('created_at')
        else:
            raise ValueError("Invalid filter_type. Must be 'payment_date', 'invoice_date', or 'all'")
        
        # Get all payments for these appointments
        appointment_ids = appointments.values_list('id', flat=True)
        payments = ChannelPayment.objects.filter(
            appointment_id__in=appointment_ids
        ).values('appointment_id').annotate(
            total_paid=Sum('amount')
        )
        
        # Create a dictionary of appointment_id to total_paid
        payments_dict = {p['appointment_id']: float(p['total_paid'] or 0) for p in payments}
        
        # Prepare the report data
        orders = []
        total_invoice_amount = 0
        total_paid_amount = 0
        total_balance = 0
        total_refund_paid_amount = 0
        total_refund_balance = 0
        total_invoice_count = 0 
        
        for appointment in appointments:
            patient = appointment.patient
    
            
            # Get customer details from patient
            customer_name = patient.name if patient else ''
            address = patient.address if patient and hasattr(patient, 'address') else ''
            mobile_number = patient.phone_number if patient and hasattr(patient, 'phone_number') else ''
            
            # Calculate payment totals
            total_amount = float(appointment.amount or 0)
            
            
            paid_amount = payments_dict.get(appointment.id, 0)
            
            balance = total_amount - paid_amount
            
            # Check if refund or deleted
            is_refund_or_deleted = appointment.is_refund or appointment.is_deleted
            
            if is_refund_or_deleted:
                total_refund_paid_amount += paid_amount
                total_refund_balance += balance
            else:
                total_invoice_amount += total_amount
                total_paid_amount += paid_amount
                total_balance += balance
                total_invoice_count += 1
            
            # Add appointment to results
            orders.append({
                'channel_id': appointment.invoice_number,
                'channel_number': str(appointment.channel_no or ''),
                'date': appointment.date.strftime("%Y-%m-%d") if appointment.date else '',
                'time': appointment.time.strftime("%H:%M:%S") if appointment.time else '',
                'customer_name': customer_name,
                'address': address,
                'mobile_number': mobile_number,
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'balance': balance,
                'bill': total_amount,  # For backward compatibility
                'is_refund': appointment.is_refund,
                'is_deleted': appointment.is_deleted
            })
        
        return {
            'orders': orders,
            'summary': {
                'total_invoice_count': total_invoice_count, 
                'total_invoice_amount': total_invoice_amount,
                'total_paid_amount': total_paid_amount,
                'total_balance': total_balance,
                'total_refund_paid_amount': total_refund_paid_amount,
                'total_refund_balance': total_refund_balance
            }
        }
        #desing how you need refudn ,delete handle
    
    @staticmethod
    def get_soldering_order_report(start_date_str, end_date_str, branch_id):
        """
        Generate a detailed soldering order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            
        Returns:
            dict: {
                'orders': [
                    {
                        'order_id': int,
                        'invoice_number': str,
                        'date': str (YYYY-MM-DD),
                        'time': str (HH:MM:SS),
                        'customer_name': str,
                        'address': str,
                        'mobile_number': str,
                        'total_amount': float,
                        'paid_amount': float,
                        'balance': float,
                        'bill': float,  # Same as total_amount for consistency
                        'status': str,
                        'progress_status': str
                    },
                    ...
                ],
                'summary': {
                    'total_invoice_count': int,
                    'total_invoice_amount': float,
                    'total_paid_amount': float,
                    'total_balance': float
                }
            }
        """
        try:
            # Parse dates properly
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date_str, end_date_str)
            
            # print(f"Soldering Order start_date: {start_date_str}, end_date: {end_date_str}")
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_datetime > end_datetime:
            raise ValueError("Start date cannot be after end date.")
            
        # Get all soldering orders in the date range for the branch
        # Fix: Use order_date__range instead of order_date__date__range since order_date is a DateField
        soldering_orders = SolderingOrder.objects.select_related('patient').prefetch_related('invoices').filter(
            order_date__range=(start_date_str, end_date_str),
            branch_id=branch_id,
            is_deleted=False
        ).order_by('order_date')
        
        # Get all payments for these orders
        order_ids = list(soldering_orders.values_list('id', flat=True))
        payments = SolderingPayment.objects.filter(
            order_id__in=order_ids,
            is_deleted=False
        ).values('order_id').annotate(
            total_paid=Sum('amount')
        )
    # print(f"SolderingPayment: {payments}")
        
        # Create a dictionary of order_id to total_paid
        payments_dict = {p['order_id']: float(p['total_paid'] or 0) for p in payments}
        
        # Prepare the report data
        orders = []
        total_invoice_amount = 0
        total_paid_amount = 0
        total_balance = 0
        total_invoice_count = soldering_orders.count()
        
        for soldering_order in soldering_orders:
            patient = soldering_order.patient
            
            # Get invoice number from the first invoice (if exists)
            invoice_number = ''
            if soldering_order.invoices.exists():
                first_invoice = soldering_order.invoices.first()
                invoice_number = first_invoice.invoice_number if first_invoice else ''
            
            # Calculate payment totals
            total_amount = float(soldering_order.price or 0)
            paid_amount = payments_dict.get(soldering_order.id, 0)
            balance = total_amount - paid_amount
            
            # Add to totals
            total_invoice_amount += total_amount
            total_paid_amount += paid_amount
            total_balance += balance
            
            # Add soldering order to results
            orders.append({
                'order_id': soldering_order.id,
                'invoice_number': invoice_number,
                'date': soldering_order.order_date.strftime("%Y-%m-%d") if soldering_order.order_date else '',
                'time': soldering_order.order_updated_date.strftime("%H:%M:%S") if soldering_order.order_updated_date else '',
                'customer_name': patient.name if patient else '',
                'address': patient.address if patient and hasattr(patient, 'address') else '',
                'mobile_number': patient.phone_number if patient and hasattr(patient, 'phone_number') else '',
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'balance': balance,
                'bill': total_amount,  # Same as total_amount for consistency
                'status': soldering_order.status,
                'progress_status': soldering_order.progress_status
            })
        
        return {
            'orders': orders,
            'summary': {
                'total_invoice_count': total_invoice_count,
                'total_invoice_amount': total_invoice_amount,
                'total_paid_amount': total_paid_amount,
                'total_balance': total_balance
            }
        }
    
    @staticmethod
    def get_hearing_order_report(start_date_str, end_date_str, branch_id, filter_type='all'):
        """
        Generate a detailed hearing order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            filter_type (str): Type of filtering - 'payment_date', 'invoice_date', or 'all'
            
        Returns:
            dict: {
                'orders': [
                    {
                        'refraction_number': str,
                        'invoice_number': str,
                        'date': str (YYYY-MM-DD),
                        'time': str (HH:MM:SS),
                        'customer_name': str,
                        'nic': str,
                        'address': str,
                        'mobile_number': str,
                        'total_amount': float,
                        'paid_amount': float,
                        'balance': float,
                        'bill': float  # Same as total_amount for backward compatibility
                    },
                    ...
                ],
                'summary': {
                    'total_invoice_amount': float,
                    'total_paid_amount': float,
                    'total_balance': float,
                    'total_refund_paid_amount': float,
                    'total_refund_balance': float
                }
            }
        """
        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date_str, end_date_str)
            
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_datetime > end_datetime:
            raise ValueError("Start date cannot be after end date.")
        
        # Get invoices based on filter type
        if filter_type == 'invoice_date':
            # Changed from OR logic to AND logic: only hearing invoices that meet ALL conditions
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer',
            ).filter(
                Q(invoice_type='hearing', invoice_date__range=(start_datetime, end_datetime))|
                 Q(invoice_type='hearing', invoice_date__range=(start_datetime, end_datetime), order__deleted_at__range=(start_datetime, end_datetime))|
                 Q(invoice_type='hearing', invoice_date__range=(start_datetime, end_datetime),order__refunded_at__range=(start_datetime, end_datetime)),
                # is_deleted=False,
                # order__is_deleted=False
            ).order_by('invoice_date')
            print(f"Hearing invoices found by invoice_date: {invoices}")
        elif filter_type == 'payment_date':
            # Filter by payment date OR orders refunded/deleted in date range
            payments = OrderPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                order__branch_id=branch_id
            ).select_related('order')
            
            payment_order_ids = payments.values_list('order_id', flat=True).distinct()
            
            # Also get orders that were refunded or deleted in this date range
            refunded_deleted_orders = Order.all_objects.filter(
                Q(expense_refunds__is_refund=True, expense_refunds__created_at__range=(start_datetime, end_datetime)) | 
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            all_order_ids = set(payment_order_ids) | set(refunded_deleted_orders)
            
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer', 'order__refraction'
            ).filter(
                order_id__in=all_order_ids,
                invoice_type='hearing',
                order__branch_id=branch_id,
                # is_deleted=False,
                # order__is_deleted=False
            ).order_by('invoice_date')
        elif filter_type == 'all':
            # Intersection logic: invoices with payments in date range AND created in date range
            # PLUS orders that were refunded/deleted in date range
            payments = OrderPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                order__branch_id=branch_id,
                order__invoice__invoice_type='hearing'
            ).select_related('order')
            
            payment_order_ids = payments.values_list('order_id', flat=True).distinct()
            
            # Get orders that were refunded or deleted in this date range
            refunded_deleted_orders = Order.all_objects.filter(
                Q(expense_refunds__is_refund=True, expense_refunds__created_at__range=(start_datetime, end_datetime)) | 
                Q(refunded_at__range=(start_datetime, end_datetime)) |
                Q(deleted_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            ).values_list('id', flat=True).distinct()
            
            # Combine payment orders and refunded/deleted orders
            all_order_ids = set(payment_order_ids) | set(refunded_deleted_orders)
            
            invoices = Invoice.all_objects.select_related(
                'order', 'order__customer', 'order__refraction'
            ).filter(
                Q(invoice_type='hearing', invoice_date__range=(start_datetime, end_datetime))|
                 Q(invoice_type='hearing',  order__deleted_at__range=(start_datetime, end_datetime))|
                 Q(invoice_type='hearing', order__refunded_at__range=(start_datetime, end_datetime)),
                order__branch_id=branch_id,
                # is_deleted=False,
                # order__is_deleted=False
            ).distinct().order_by('invoice_date')
        else:
            raise ValueError("Invalid filter_type. Must be 'payment_date', 'invoice_date', or 'all'")
        
        # Get all payments for these orders
        order_ids = invoices.values_list('order_id', flat=True)
        payments = OrderPayment.objects.filter(
            order_id__in=order_ids
        ).values('order_id').annotate(
            total_paid=Sum('amount')
        )
        
        # Create a dictionary of order_id to total_paid
        payments_dict = {p['order_id']: float(p['total_paid'] or 0) for p in payments}
        
        # Prepare the report data
        orders = []
        total_invoice_amount = 0
        total_paid_amount = 0
        total_balance = 0
        total_refund_paid_amount = 0
        total_refund_balance = 0
        total_invoice_count = 0 
        # provided date range sum of expence order refunds 
        refund_amount = Expense.objects.filter(
            created_at__range=(start_datetime, end_datetime),
            order_refund__isnull=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        total_refund_paid_amount += float(refund_amount)
        print(f"Refund amount in date range: {refund_amount}")
        for invoice in invoices:
            order = invoice.order
            customer = order.customer
    
            
            # Get customer details from refraction if available, otherwise from patient
            
            # refraction_number = refraction. or ''
            customer_name = customer.name
            nic = customer.nic or ''
            address = customer.address or ''
            mobile_number = customer.phone_number or ''
            
            # Calculate payment totals
            total_amount = float(order.total_price)
            
            
            paid_amount = float(order.total_payment)
            
            balance = total_amount - paid_amount
            
            # Check if refund or deleted
            is_refund_or_deleted = order.is_refund or invoice.is_deleted or order.is_deleted
            
            if is_refund_or_deleted:
                total_refund_paid_amount += paid_amount
                total_refund_balance += balance
            else:
                total_invoice_amount += total_amount
                total_paid_amount += paid_amount
                total_balance += balance
                total_invoice_count += 1
            
            # Add order to results
            orders.append({
                # 'refraction_number': refraction_number,
                'invoice_number': invoice.invoice_number or '',
                'date': invoice.invoice_date.strftime("%Y-%m-%d"),
                'time': invoice.invoice_date.strftime("%H:%M:%S"),
                'customer_name': customer_name,
                'nic': nic or '',
                'address': address or '',
                'mobile_number': mobile_number or '',
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'balance': balance,
                'bill': total_amount,  # For backward compatibility
                'is_refund': order.is_refund,
                'is_deleted': invoice.is_deleted or order.is_deleted
            })
        
        return {
            'orders': orders,
            'summary': {
                'total_invoice_count': total_invoice_count, 
                'total_invoice_amount': total_invoice_amount,
                'total_paid_amount': total_paid_amount,
                'total_balance': total_balance,
                'total_refund_paid_amount': total_refund_paid_amount,
                'total_refund_balance': total_refund_balance
            }
        }
        #desing how you need refudn ,delete handle


