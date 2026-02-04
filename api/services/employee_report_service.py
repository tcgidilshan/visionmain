from django.db.models import Sum, Count, Q, Case, When, IntegerField
from django.utils import timezone
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models import Order, CustomUser, OrderItem, Frame, Lens, Branch, OrderFeedback


class EmployeeReportService:
    """
    Service class for generating employee history reports based on sales performance.
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
    def get_employee_history_report(
        start_date: datetime,
        end_date: datetime,
        employee_code: str = None,
        branch_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        Generate employee history report based on sales performance within date range.
        
        Args:
            start_date: Start date for filtering orders
            end_date: End date for filtering orders
            employee_code: Optional specific employee code to filter by
            branch_id: Optional branch ID to filter by
            
        Returns:
            List of dictionaries containing employee performance data
        """
        
        # Base query for orders within date range
        orders_query = Order.objects.filter(
            order_date__range=[start_date, end_date],
            is_deleted=False,
            sales_staff_code__isnull=False
        )
        
        # Filter by branch if provided
        if branch_id:
            orders_query = orders_query.filter(branch_id=branch_id)
        
        # Filter by specific employee if provided
        if employee_code:
            orders_query = orders_query.filter(
                sales_staff_code__user_code=employee_code
            )
        
        # Get all employees who have activity in the date range
        # This includes: created orders, submitted feedback, or issued glasses
        employees_with_orders = CustomUser.objects.filter(
            orders__in=orders_query
        )
        
        # Build base queries for feedback and glass issuing
        feedback_orders_query = Order.objects.filter(
            order_date__range=[start_date, end_date],
            is_deleted=False
        )
        issued_orders_query = Order.objects.filter(
            order_date__range=[start_date, end_date],
            is_deleted=False,
            issued_by__isnull=False
        )
        
        if branch_id:
            feedback_orders_query = feedback_orders_query.filter(branch_id=branch_id)
            issued_orders_query = issued_orders_query.filter(branch_id=branch_id)
        
        employees_with_feedback = CustomUser.objects.filter(
            order_feedback__order__in=feedback_orders_query
        )
        
        employees_with_glass_issued = CustomUser.objects.filter(
            issued_orders__in=issued_orders_query
        )
        
        # Combine all employees with any activity
        employees = (employees_with_orders | employees_with_feedback | employees_with_glass_issued).distinct()
        
        # Filter by specific employee code if provided
        if employee_code:
            employees = employees.filter(user_code=employee_code)
        
        result = []
        
        for employee in employees:
            # Get employee's orders in the date range (orders created by this employee)
            employee_orders = orders_query.filter(
                sales_staff_code=employee
            )
            
            # Get order items for this employee's orders
            order_items = OrderItem.objects.filter(
                order__in=employee_orders,
                is_deleted=False
            )
            
            # Get feedback submitted by this employee (regardless of who created the order)
            # This correctly attributes feedback to the user who submitted it
            feedback_base_query = OrderFeedback.objects.filter(
                user=employee,
                order__order_date__range=[start_date, end_date],
                order__is_deleted=False
            )
            
            # Apply branch filter if provided
            if branch_id:
                feedback_base_query = feedback_base_query.filter(order__branch_id=branch_id)
            
            feedback_counts = feedback_base_query.aggregate(
                rating_1=Count('id', filter=Q(rating=1)),
                rating_2=Count('id', filter=Q(rating=2)),
                rating_3=Count('id', filter=Q(rating=3)),
                rating_4=Count('id', filter=Q(rating=4)),
                total_feedback=Count('id')
            )
            
            # Count branded frames sold
            branded_frames_count = order_items.filter(
                frame__isnull=False,
                frame__brand_type='branded'
            ).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            # Count branded lenses sold
            branded_lenses_count = order_items.filter(
                external_lens__isnull=False,
                external_lens__branded='branded'
            ).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            # Count factory orders (orders with invoice_type='factory')
            factory_orders_count = employee_orders.filter(
                invoice__invoice_type='factory'
            ).count()
            
            # Count normal orders (orders with invoice_type='normal')
            normal_orders_count = employee_orders.filter(
                invoice__invoice_type='normal'
            ).count()
            
            # Count glass sender orders (orders where THIS employee issued the glasses)
            # This correctly attributes glass issuing to the user who performed the action
            glass_sender_base_query = Order.objects.filter(
                order_date__range=[start_date, end_date],
                is_deleted=False,
                issued_by=employee
            )
            
            # Apply branch filter if provided
            if branch_id:
                glass_sender_base_query = glass_sender_base_query.filter(branch_id=branch_id)
            
            glass_sender_count = glass_sender_base_query.count()
            
            # Customer feedback count
            customer_feedback_count = feedback_counts['total_feedback']
            
            # Calculate total count
            total_count = (
                branded_frames_count + 
                branded_lenses_count + 
                factory_orders_count + 
                normal_orders_count + 
                customer_feedback_count
            )
            
            # Calculate total sales amount for this employee
            total_sales = employee_orders.aggregate(
                total=Sum('total_price')
            )['total'] or 0
            
            # Get branch info - prioritize from orders created by employee, 
            # then from feedback orders, then from glass issued orders
            branch_info = None
            if branch_id:
                # If filtering by branch, use that branch info
                try:
                    branch = Branch.objects.get(id=branch_id)
                    branch_info = {
                        'id': branch.id,
                        'name': branch.branch_name,
                        'location': branch.location
                    }
                except Branch.DoesNotExist:
                    pass
            elif employee_orders.exists():
                first_order_branch = employee_orders.first().branch
                if first_order_branch:
                    branch_info = {
                        'id': first_order_branch.id,
                        'name': first_order_branch.branch_name,
                        'location': first_order_branch.location
                    }
            elif feedback_base_query.exists():
                # Get branch from feedback orders
                first_feedback = feedback_base_query.first()
                if first_feedback and first_feedback.order.branch:
                    branch_info = {
                        'id': first_feedback.order.branch.id,
                        'name': first_feedback.order.branch.branch_name,
                        'location': first_feedback.order.branch.location
                    }
            elif glass_sender_base_query.exists():
                # Get branch from glass issued orders
                first_issued = glass_sender_base_query.first()
                if first_issued and first_issued.branch:
                    branch_info = {
                        'id': first_issued.branch.id,
                        'name': first_issued.branch.branch_name,
                        'location': first_issued.branch.location
                    }
            
            employee_data = {
                'employee_id': employee.id,
                'user_code': employee.user_code or 'N/A',
                'username': employee.username,
                'full_name': f"{employee.first_name} {employee.last_name}".strip() or employee.username,
                'branded_frames_sold_count': int(branded_frames_count),
                'branded_lenses_sold_count': int(branded_lenses_count),
                'factory_order_count': factory_orders_count,
                'normal_order_count': normal_orders_count,
                'glass_sender_count': glass_sender_count,
                'customer_feedback_count': customer_feedback_count,
                'feedback_ratings': {
                    'rating_1': feedback_counts['rating_1'],
                    'rating_2': feedback_counts['rating_2'],
                    'rating_3': feedback_counts['rating_3'],
                    'rating_4': feedback_counts['rating_4']
                },
                'total_count': int(total_count),
                'total_sales_amount': float(total_sales),
                'total_orders': employee_orders.count(),
                'branch': branch_info
            }
            
            result.append(employee_data)
        
        # Sort by total_count descending
        result.sort(key=lambda x: x['total_count'], reverse=True)
        
        return result
    
    @staticmethod
    def get_report_summary(
        start_date: datetime,
        end_date: datetime,
        branch_id: int = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for the employee history report.
        
        Args:
            start_date: Start date for filtering orders
            end_date: End date for filtering orders
            branch_id: Optional branch ID to filter by
            
        Returns:
            Dictionary containing summary statistics
        """
        
        # Get all orders in date range
        all_orders = Order.objects.filter(
            order_date__range=[start_date, end_date],
            is_deleted=False,
            sales_staff_code__isnull=False
        )
        
        # Filter by branch if provided
        if branch_id:
            all_orders = all_orders.filter(branch_id=branch_id)
        
        # Get all order items in date range
        all_order_items = OrderItem.objects.filter(
            order__in=all_orders,
            is_deleted=False
        )
        
        # Calculate totals
        total_employees = CustomUser.objects.filter(
            orders__in=all_orders
        ).distinct().count()
        
        total_orders = all_orders.count()
        total_revenue = all_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        total_frames_sold = all_order_items.filter(
            frame__isnull=False
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        total_lenses_sold = all_order_items.filter(
            lens__isnull=False
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        factory_orders = all_orders.filter(invoice__invoice_type='factory').count()
        normal_orders = all_orders.filter(invoice__invoice_type='normal').count()
        
        # Count glass sender orders (orders where issued_by is not null)
        glass_sender_orders = all_orders.filter(issued_by__isnull=False).count()
        
        # Get branch info if filtering by branch
        branch_info = None
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
                branch_info = {
                    'id': branch.id,
                    'name': branch.branch_name,
                    'location': branch.location
                }
            except Branch.DoesNotExist:
                pass
        
        return {
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'branch': branch_info,
            'totals': {
                'active_employees': total_employees,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'total_frames_sold': int(total_frames_sold),
                'total_lenses_sold': int(total_lenses_sold),
                'factory_orders': factory_orders,
                'normal_orders': normal_orders,
                'glass_sender_orders': glass_sender_orders
            },
            'averages': {
                'avg_revenue_per_employee': float(total_revenue / total_employees) if total_employees > 0 else 0,
                'avg_orders_per_employee': total_orders / total_employees if total_employees > 0 else 0,
                'avg_items_per_order': (total_frames_sold + total_lenses_sold) / total_orders if total_orders > 0 else 0
            }
        }