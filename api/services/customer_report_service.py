from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models import Order, Patient, OrderPayment,Invoice,Appointment
class CustomerReportService:
    """
    Service class for generating customer reports based on factory orders.
    """
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> tuple:
        """
        Validate and convert date strings to datetime objects.
        
        Args:
            start_date: Start date string in YYYY-MM-DD format
            end_date: End date string in YYYY-MM-DD format
            
        Returns:
            Tuple of (start_datetime, end_datetime) or raises ValueError
        """
        
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Set end date to end of day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            
            if start_dt > end_dt:
                raise ValueError("Start date cannot be after end date")
            
            return start_dt, end_dt
            
        except ValueError as e:
            if "time data" in str(e):
                raise ValueError("Invalid date format. Use YYYY-MM-DD format")
            raise e
    
    @staticmethod
    def get_best_customers_report(
        start_date: datetime,
        end_date: datetime,
        min_budget: float
    ) -> List[Dict[str, Any]]:
        """
        Generate best customers report based on factory orders within date range
        and minimum budget criteria.
        
        Args:
            start_date: Start date for filtering orders
            end_date: End date for filtering orders
            min_budget: Minimum budget amount to filter customers
            
        Returns:
            List of dictionaries containing customer information and order statistics
        """
        
        # Filter factory orders within the date range
        # Assuming factory orders are identified by specific criteria
        # You may need to adjust this based on your business logic
        factory_orders = Order.objects.filter(
            order_date__range=[start_date, end_date],
            is_deleted=False,
            # Add any specific criteria that identifies factory orders
            # For example: is_factory_order=True or specific status
        )
        
        # Get customer aggregated data
        customer_data = factory_orders.values(
            'customer__id',
            'customer__name',
            'customer__nic',
            'customer__address',
            'customer__phone_number'
        ).annotate(
            total_amount=Sum('total_price'),
            order_count=Count('id')
        ).filter(
            total_amount__gte=min_budget
        ).order_by('-total_amount')
        
        # Format the results
        result = []
        for customer in customer_data:
            result.append({
                'customer_id': customer['customer__id'],
                'customer_name': customer['customer__name'],
                'nic': customer['customer__nic'] or 'N/A',
                'address': customer['customer__address'] or 'N/A',
                'mobile_number': customer['customer__phone_number'] or 'N/A',
                'total_factory_order_amount': float(customer['total_amount']),
                'number_of_orders': customer['order_count']
            })
        
        return result
    
    @staticmethod
    def get_customer_factory_orders_detail(
        customer_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific customer's factory orders.
        
        Args:
            customer_id: ID of the customer
            start_date: Start date for filtering orders
            end_date: End date for filtering orders
            
        Returns:
            Dictionary containing detailed customer and order information
        """
        
        try:
            customer = Patient.objects.get(id=customer_id)
        except Patient.DoesNotExist:
            return None
        
        # Get factory orders for this customer
        factory_orders = Order.objects.filter(
            customer_id=customer_id,
            order_date__range=[start_date, end_date],
            is_deleted=False
        ).select_related('customer', 'sales_staff_code')
        
        # Get order details
        orders_detail = []
        total_amount = 0
        
        for order in factory_orders:
            # Get payments for this order
            payments = OrderPayment.objects.filter(
                order=order,
                is_deleted=False
            ).aggregate(
                total_paid=Sum('amount')
            )
            
            order_detail = {
                'order_id': order.id,
                'order_date': order.order_date,
                'status': order.get_status_display(),
                'sub_total': float(order.sub_total),
                'discount': float(order.discount or 0),
                'total_price': float(order.total_price),
                'total_paid': float(payments['total_paid'] or 0),
                'sales_staff': order.sales_staff_code.get_full_name() if order.sales_staff_code else 'N/A',
                'is_urgent': order.urgent,
                'fitting_status': order.get_fitting_status_display()
            }
            orders_detail.append(order_detail)
            total_amount += order.total_price
        
        return {
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'nic': customer.nic or 'N/A',
                'address': customer.address or 'N/A',
                'phone_number': customer.phone_number or 'N/A',
                'date_of_birth': customer.date_of_birth
            },
            'orders': orders_detail,
            'summary': {
                'total_orders': len(orders_detail),
                'total_amount': float(total_amount),
                'date_range': {
                    'start': start_date,
                    'end': end_date
                }
            }
        }
    
    @staticmethod
    def get_report_summary(
        start_date: datetime,
        end_date: datetime,
        min_budget: float
    ) -> Dict[str, Any]:
        """
        Get summary statistics for the best customers report.
        
        Args:
            start_date: Start date for filtering orders
            end_date: End date for filtering orders
            min_budget: Minimum budget amount
            
        Returns:
            Dictionary containing summary statistics
        """
        
        # Get all factory orders in date range
        all_factory_orders = Order.objects.filter(
            order_date__range=[start_date, end_date],
            is_deleted=False
        )
        
        # Get qualifying customers
        qualifying_customers = all_factory_orders.values('customer__id').annotate(
            total_amount=Sum('total_price')
        ).filter(
            total_amount__gte=min_budget
        )
        
        # Calculate statistics
        total_customers = all_factory_orders.values('customer__id').distinct().count()
        qualifying_customers_count = qualifying_customers.count()
        
        total_revenue = all_factory_orders.aggregate(
            total=Sum('total_price')
        )['total'] or 0
        
        qualifying_revenue = sum(
            customer['total_amount'] for customer in qualifying_customers
        )
        
        return {
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'criteria': {
                'min_budget': min_budget
            },
            'statistics': {
                'total_customers': total_customers,
                'qualifying_customers': qualifying_customers_count,
                'total_factory_orders': all_factory_orders.count(),
                'total_revenue': float(total_revenue),
                'qualifying_revenue': float(qualifying_revenue),
                'percentage_qualifying': (
                    qualifying_customers_count / total_customers * 100 
                    if total_customers > 0 else 0
                )
            }
        }

class CustomerLocationReportService:
    """
    Service class for generating customer location reports.
    Provides methods to filter customers (patients) by district and town,
    and retrieve relevant details for the location-based report.
    """
    
    @staticmethod
    def get_customers_table_data(district: str, town: str, branch_id: Optional[int] = None) -> List[Dict]:
        """
        Get customer table data filtered by district and town.
        Returns only the essential fields needed for the table display.
        
        Args:
            district (str): District name to filter by
            town (str): Town name to filter by
            branch_id (Optional[int]): Branch ID to filter by specific branch
            
        Returns:
            List[Dict]: List of customer table data with required fields only
        """
        
        # Build the address filter - case insensitive search
        address_filter = Q(
            address__icontains=district
        ) & Q(
            address__icontains=town
        )
        
        # Base query for patients with address filter
        patients_query = Patient.objects.filter(address_filter).exclude(
            address__isnull=True
        ).exclude(address__exact='')
        
        customers_table_data = []
        
        for patient in patients_query:
            # Get orders for this patient
            orders_query = Order.objects.filter(customer=patient)
            
            # Filter by branch if provided
            if branch_id:
                orders_query = orders_query.filter(branch_id=branch_id)
            
            # Get the most recent order for invoice details
            latest_order = orders_query.order_by('-order_date').first()
            
            if latest_order:
                # Try to get invoice for the order
                invoice_number = None
                transaction_date = latest_order.order_date
                
                try:
                    invoice = Invoice.objects.get(order=latest_order)
                    invoice_number = invoice.invoice_number
                    transaction_date = invoice.invoice_date
                except Invoice.DoesNotExist:
                    # If no invoice, use order ID as reference
                    invoice_number = f"ORD-{latest_order.id}"
                
                # Calculate age if date_of_birth is available
                age = None
                if patient.date_of_birth:
                    today = timezone.now().date()
                    age = today.year - patient.date_of_birth.year
                    if today.month < patient.date_of_birth.month or \
                       (today.month == patient.date_of_birth.month and today.day < patient.date_of_birth.day):
                        age -= 1
                
                # Return only the required table fields
                customer_data = {
                    'invoice_number': invoice_number,
                    'customer_name': patient.name,
                    'mobile_number': patient.phone_number or '',
                    'address': patient.address,
                    'date': transaction_date.strftime('%Y-%m-%d') if hasattr(transaction_date, 'strftime') else str(transaction_date),
                    'age': age
                }
                
                customers_table_data.append(customer_data)
            
            else:
                # Patient exists but no orders - check if they have appointments
                appointments_query = Appointment.objects.filter(patient=patient)
                
                if branch_id:
                    appointments_query = appointments_query.filter(branch_id=branch_id)
                
                latest_appointment = appointments_query.order_by('-created_at').first()
                
                if latest_appointment:
                    # Calculate age
                    age = None
                    if patient.date_of_birth:
                        today = timezone.now().date()
                        age = today.year - patient.date_of_birth.year
                        if today.month < patient.date_of_birth.month or \
                           (today.month == patient.date_of_birth.month and today.day < patient.date_of_birth.day):
                            age -= 1
                    
                    # Return only the required table fields
                    customer_data = {
                        'invoice_number': f"APT-{latest_appointment.invoice_number}" if latest_appointment.invoice_number else f"APT-{latest_appointment.id}",
                        'customer_name': patient.name,
                        'mobile_number': patient.phone_number or '',
                        'address': patient.address,
                        'date': latest_appointment.date.strftime('%Y-%m-%d'),
                        'age': age
                    }
                    
                    customers_table_data.append(customer_data)
        
        # Sort by date (most recent first)
        customers_table_data.sort(key=lambda x: x['date'], reverse=True)
        
        return customers_table_data
    
    @staticmethod
    def get_available_locations() -> Dict[str, List[str]]:
        """
        Get all available districts and towns from patient addresses.
        
        Returns:
            Dict[str, List[str]]: Dictionary with districts as keys and list of towns as values
        """
        
        # Get all non-empty addresses
        addresses = Patient.objects.exclude(
            address__isnull=True
        ).exclude(
            address__exact=''
        ).values_list('address', flat=True).distinct()
        
        location_data = {}
        
        for address in addresses:
            if address:
                # Simple parsing - you might want to improve this based on your address format
                address_parts = [part.strip() for part in address.split(',')]
                
                if len(address_parts) >= 2:
                    # Assume last part is district, second last is town
                    district = address_parts[-1].strip()
                    town = address_parts[-2].strip()
                    
                    if district not in location_data:
                        location_data[district] = []
                    
                    if town not in location_data[district]:
                        location_data[district].append(town)
        
        # Sort districts and towns alphabetically
        for district in location_data:
            location_data[district].sort()
        
        return dict(sorted(location_data.items()))
    
    @staticmethod
    def get_customer_statistics_by_location(district: str, town: str, branch_id: Optional[int] = None) -> Dict:
        """
        Get statistics for customers in a specific location.
        
        Args:
            district (str): District name
            town (str): Town name
            branch_id (Optional[int]): Branch ID to filter by
            
        Returns:
            Dict: Statistics including total customers, orders, revenue, etc.
        """
        
        customers = CustomerLocationReportService.get_customers_table_data(district, town, branch_id)
        
        total_customers = len(customers)
        total_orders = 0
        total_revenue = 0
        age_groups = {'0-18': 0, '19-35': 0, '36-50': 0, '51-65': 0, '65+': 0, 'unknown': 0}
        
        for customer in customers:
            if 'order_id' in customer:
                total_orders += 1
                
                # Get order total for revenue calculation
                try:
                    order = Order.objects.get(id=customer['order_id'])
                    total_revenue += float(order.total_price)
                except Order.DoesNotExist:
                    pass
            
            # Age group classification
            age = customer.get('age')
            if age is None:
                age_groups['unknown'] += 1
            elif age <= 18:
                age_groups['0-18'] += 1
            elif age <= 35:
                age_groups['19-35'] += 1
            elif age <= 50:
                age_groups['36-50'] += 1
            elif age <= 65:
                age_groups['51-65'] += 1
            else:
                age_groups['65+'] += 1
        
        return {
            'total_customers': total_customers,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'age_groups': age_groups,
            'district': district,
            'town': town
        }