from datetime import datetime, time
from django.db.models import Sum, Q
from api.models import Invoice, OrderPayment,Appointment, ChannelPayment, SolderingPayment, SolderingOrder,SolderingInvoice
from django.utils import timezone

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
        
        print(f"Date range for query: {start_datetime} to {end_datetime}")
        
        payments = OrderPayment.objects.select_related("order").filter(
            payment_date__range=(start_datetime, end_datetime),
            order__branch_id=branch_id
        )
        # print(f"Found {payments.count()} payments")

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

            payments_by_order[oid][payment.payment_method] += float(payment.amount)
            payments_by_order[oid]["total"] += float(payment.amount)

        # Debug: Print the payments_by_order keys (order IDs)
        # print(f"\nOrders with payments: {list(payments_by_order.keys())}")
        
        # Get all invoices where related order has at least 1 payment on that date
        invoice_qs = Invoice.objects.select_related("order").filter(
            order_id__in=payments_by_order.keys(),
            order__branch_id=branch_id,
            is_deleted=False,
            order__is_deleted=False
        )
        
        # print(f"Found {invoice_qs.count()} invoices for these orders")

        results = []

        for invoice in invoice_qs:
            order_id = invoice.order_id
            payment_data = payments_by_order.get(order_id, {})

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
                "total_payment": payment_data.get("total", 0),
                "balance": float(invoice.order.total_price) - payment_data.get("total", 0)
            }

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

            soldering_payments_by_order[oid][payment.payment_method] += float(payment.amount)
            soldering_payments_by_order[oid]["total"] += float(payment.amount)

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
                "total_payment": payment_data.get("total", 0),
                "balance": float(invoice.order.price) - payment_data.get("total", 0)
            }

            results.append(data)
        return results
    
    @staticmethod
    def get_factory_order_report(start_date_str, end_date_str, branch_id):
        """
        Generate a detailed factory order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            
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
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")
            
        # Get all factory invoices in the date range for the branch
        invoices = Invoice.objects.select_related(
            'order', 'order__customer', 'order__refraction'
        ).filter(
            invoice_type='factory',
            invoice_date__date__range=(start_date, end_date),
            order__branch_id=branch_id,
            is_deleted=False,
            order__is_deleted=False
        ).order_by('invoice_date')
        
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
        total_invoice_count = invoices.count() 
        
        for invoice in invoices:
            order = invoice.order
            customer = order.customer
            refraction = order.refraction
            
            # Get customer details from refraction if available, otherwise from patient
            if refraction:
                customer_name = refraction.customer_full_name
                nic = refraction.nic or ''
                address = ''  # Address not directly on refraction, would need to be added if needed
                mobile_number = refraction.customer_mobile or ''
                refraction_number = refraction.refraction_number or ''
            else:
                customer_name = customer.name
                nic = customer.nic or ''
                address = customer.address or ''
                mobile_number = customer.phone_number or ''
                refraction_number = ''
            
            # Calculate payment totals
            total_amount = float(order.total_price)
            paid_amount = payments_dict.get(order.id, 0)
            balance = total_amount - paid_amount
            
            # Add to totals
            total_invoice_amount += total_amount
            total_paid_amount += paid_amount
            total_balance += balance
            
            # Add order to results
            orders.append({
                'refraction_number': refraction_number,
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
                'bill': total_amount  # For backward compatibility
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
    def get_normal_order_report(start_date_str, end_date_str, branch_id):
        """
        Generate a detailed normal order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            
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
                    'total_balance': float
                }
            }
        """
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")
            
        # Get all normal invoices in the date range for the branch
        invoices = Invoice.objects.select_related(
            'order', 'order__customer', 'order__refraction'
        ).filter(
            invoice_type='normal',  # Changed from 'factory' to 'manual' for normal orders
            invoice_date__date__range=(start_date, end_date),
            order__branch_id=branch_id,
            is_deleted=False,
            order__is_deleted=False
        ).order_by('invoice_date')
        
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
        total_invoice_count = invoices.count()
        
        for invoice in invoices:
            order = invoice.order
            customer = order.customer
            refraction = order.refraction
            
            # Get customer details from refraction if available, otherwise from patient
            if refraction:
                customer_name = refraction.customer_full_name
                nic = refraction.nic or ''
                address = ''  # Address not directly on refraction
                mobile_number = refraction.customer_mobile or ''
                refraction_number = refraction.refraction_number or ''
            else:
                customer_name = customer.name
                nic = customer.nic or ''
                address = customer.address or ''
                mobile_number = customer.phone_number or ''
                refraction_number = ''
            
            # Calculate payment totals
            total_amount = float(order.total_price)
            paid_amount = payments_dict.get(order.id, 0)
            balance = total_amount - paid_amount
            
            # Add to totals
            total_invoice_amount += total_amount
            total_paid_amount += paid_amount
            total_balance += balance
            
            # Add order to results
            orders.append({
                'refraction_number': refraction_number,
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
                'bill': total_amount  # Same as total_amount for consistency
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
    def get_channel_order_report(start_date_str, end_date_str, branch_id):
        """
        Generate a detailed channel order report filtered by date range and branch.
        
        Args:
            start_date_str (str): Start date in YYYY-MM-DD format
            end_date_str (str): End date in YYYY-MM-DD format
            branch_id (int): Branch ID to filter by
            
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
                    'total_balance': float
                }
            }
        """
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")
            
        # Get all appointments in the date range for the branch
        appointments = Appointment.objects.select_related('patient').filter(
            date__range=(start_date, end_date),
            branch_id=branch_id,
            is_deleted=False
        ).order_by('date', 'time')
        
        # Get all payments for these appointments
        appointment_ids = list(appointments.values_list('id', flat=True))
        payments = ChannelPayment.objects.filter(
            appointment_id__in=appointment_ids,
            is_deleted=False
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
        total_invoice_count = appointments.count()
        
        for appointment in appointments:
            patient = appointment.patient
            
            # Calculate payment totals
            total_amount = float(appointment.amount or 0)
            paid_amount = payments_dict.get(appointment.id, 0)
            balance = total_amount - paid_amount
            
            # Add to totals
            total_invoice_amount += total_amount
            total_paid_amount += paid_amount
            total_balance += balance
            
            # Add appointment to results
            orders.append({
                'channel_id': appointment.id,
                'channel_number': str(appointment.channel_no or ''),
                'date': appointment.date.strftime("%Y-%m-%d") if appointment.date else '',
                'time': appointment.time.strftime("%H:%M:%S") if appointment.time else '',
                'customer_name': patient.name if patient else '',
                'address': patient.address if patient and hasattr(patient, 'address') else '',
                'mobile_number': patient.phone_number if patient and hasattr(patient, 'phone_number') else '',
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'balance': balance,
                'bill': total_amount  # Same as total_amount for consistency
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
            #add time zone to the date
           # Parse dates
            start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            # Convert to timezone-aware datetimes for the start and end of the day
            start_date = timezone.make_aware(
                datetime.combine(start, time.min)
            )
            end_date = timezone.make_aware(
                datetime.combine(end, time.max)
            )
            print(f"Soldering Order start_date: {start_date}, end_date: {end_date}")
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")
            
        # Get all soldering orders in the date range for the branch
        soldering_orders = SolderingOrder.objects.select_related('patient').filter(
            order_date__date__range=(start_date, end_date),
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
        print(f"SolderingPayment: {payments}")
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
        

