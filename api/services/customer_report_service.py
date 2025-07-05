from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models import Order, Patient, OrderPayment


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