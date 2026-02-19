from django.db.models import Sum, Count, Q, Case, When, IntegerField
from django.utils import timezone
from datetime import datetime
from .time_zone_convert_service import TimezoneConverterService
from typing import List, Dict, Any, Optional
from ..models import Order, CustomUser, OrderItem, Frame, Lens, Branch, OrderFeedback


class EmployeeReportService:
    """
    Service class for generating employee history reports based on sales performance.
    """
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> tuple:
        """
        Validate and convert date strings to timezone-aware datetime objects using TimezoneConverterService.
        Args:
            start_date: Start date string in YYYY-MM-DD format
            end_date: End date string in YYYY-MM-DD format
        Returns:
            Tuple of (start_datetime, end_datetime) or raises ValueError
        """
        start_dt, end_dt = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
        if not start_dt or not end_dt:
            raise ValueError("Invalid date format. Use YYYY-MM-DD format")
        if start_dt > end_dt:
            raise ValueError("Start date cannot be after end date")
        return start_dt, end_dt
    
    @staticmethod
    def get_employee_history_report(
        start_date: datetime,
        end_date: datetime,
        employee_code: str = None,
        branch_id: int = None
    ) -> List[Dict[str, Any]]:
        import time
        t0 = time.time()
        print(f"[DEBUG][ERS] get_employee_history_report called (t=0.000s)")
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
        print(f"[DEBUG][ERS] Step 1: Querying orders (t={time.time()-t0:.3f}s)")
        orders_query = Order.objects.filter(
            order_date__range=[start_date, end_date],
            is_deleted=False,
            sales_staff_code__isnull=False
        )
        print(f"[DEBUG][ERS] orders_query count: {orders_query.count()} (t={time.time()-t0:.3f}s)")

        # Filter by branch if provided
        if branch_id:
            orders_query = orders_query.filter(branch_id=branch_id)
            print(f"[DEBUG][ERS] orders_query filtered by branch_id={branch_id}, count: {orders_query.count()} (t={time.time()-t0:.3f}s)")

        # Filter by specific employee if provided
        if employee_code:
            orders_query = orders_query.filter(
                sales_staff_code__user_code=employee_code
            )
            print(f"[DEBUG][ERS] orders_query filtered by employee_code={employee_code}, count: {orders_query.count()} (t={time.time()-t0:.3f}s)")

        # Get all employees who have activity in the date range
        print(f"[DEBUG][ERS] Step 2: Querying employees with orders (t={time.time()-t0:.3f}s)")
        employees_with_orders = CustomUser.objects.filter(
            orders__in=orders_query
        )
        print(f"[DEBUG][ERS] employees_with_orders count: {employees_with_orders.count()} (t={time.time()-t0:.3f}s)")

        # Build base queries for feedback and glass issuing
        print(f"[DEBUG][ERS] Step 3: Querying feedback and issued orders (t={time.time()-t0:.3f}s)")
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
        print(f"[DEBUG][ERS] feedback_orders_query count: {feedback_orders_query.count()} (t={time.time()-t0:.3f}s)")
        print(f"[DEBUG][ERS] issued_orders_query count: {issued_orders_query.count()} (t={time.time()-t0:.3f}s)")

        employees_with_feedback = CustomUser.objects.filter(
            order_feedback__created_at__range=[start_date, end_date],
            order_feedback__order__is_deleted=False
        )
        print(f"[DEBUG][ERS] employees_with_feedback count: {employees_with_feedback.count()} (t={time.time()-t0:.3f}s)")

        employees_with_glass_issued = CustomUser.objects.filter(
            issued_orders__in=issued_orders_query
        )
        print(f"[DEBUG][ERS] employees_with_glass_issued count: {employees_with_glass_issued.count()} (t={time.time()-t0:.3f}s)")

        # Combine all employees with any activity
        print(f"[DEBUG][ERS] Step 4: Combining employees (t={time.time()-t0:.3f}s)")
        order_ids = set(employees_with_orders.values_list('id', flat=True))
        feedback_ids = set(employees_with_feedback.values_list('id', flat=True))
        glass_issued_ids = set(employees_with_glass_issued.values_list('id', flat=True))
        all_ids = order_ids | feedback_ids | glass_issued_ids
        employees = CustomUser.objects.filter(id__in=all_ids)
        print(f"[DEBUG][ERS] employees combined count: {employees.count()} (t={time.time()-t0:.3f}s)")

        # Filter by specific employee code if provided
        if employee_code:
            employees = employees.filter(user_code=employee_code)
            print(f"[DEBUG][ERS] employees filtered by user_code={employee_code}, count: {employees.count()} (t={time.time()-t0:.3f}s)")

        result = []
        print(f"[DEBUG][ERS] Step 5: Looping employees (t={time.time()-t0:.3f}s)")
        for idx, employee in enumerate(employees):
            t_emp = time.time()
            print(f"[DEBUG][ERS] Employee {idx+1}/{employees.count()} id={employee.id} (t={time.time()-t0:.3f}s)")
            # Get employee's orders in the date range (orders created by this employee)
            employee_orders = orders_query.filter(
                sales_staff_code=employee
            )
            print(f"[DEBUG][ERS]   employee_orders count: {employee_orders.count()} (t={time.time()-t_emp:.3f}s)")

            # Get order items for this employee's orders
            order_items = OrderItem.objects.filter(
                order__in=employee_orders,
                is_deleted=False
            )
            print(f"[DEBUG][ERS]   order_items count: {order_items.count()} (t={time.time()-t_emp:.3f}s)")

            # Get feedback submitted by this employee within the date range
            feedback_base_query = OrderFeedback.objects.filter(
                user=employee,
                created_at__range=[start_date, end_date],
                order__is_deleted=False
            )
            if branch_id:
                feedback_base_query = feedback_base_query.filter(order__branch_id=branch_id)
            print(f"[DEBUG][ERS]   feedback_base_query count: {feedback_base_query.count()} (t={time.time()-t_emp:.3f}s)")

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
            print(f"[DEBUG][ERS]   branded_frames_count: {branded_frames_count}")

            # Count branded lenses sold
            branded_lenses_count = order_items.filter(
                external_lens__isnull=False,
                external_lens__branded='branded'
            ).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            print(f"[DEBUG][ERS]   branded_lenses_count: {branded_lenses_count}")

            # Count factory orders (orders with invoice_type='factory')
            factory_orders_count = employee_orders.filter(
                invoice__invoice_type='factory'
            ).count()
            print(f"[DEBUG][ERS]   factory_orders_count: {factory_orders_count}")

            # Count normal orders (orders with invoice_type='normal')
            normal_orders_count = employee_orders.filter(
                invoice__invoice_type='normal'
            ).count()
            print(f"[DEBUG][ERS]   normal_orders_count: {normal_orders_count}")

            # Count glass sender orders (orders where THIS employee issued the glasses)
            glass_sender_base_query = Order.objects.filter(
                order_date__range=[start_date, end_date],
                is_deleted=False,
                issued_by=employee
            )
            if branch_id:
                glass_sender_base_query = glass_sender_base_query.filter(branch_id=branch_id)
            glass_sender_count = glass_sender_base_query.count()
            print(f"[DEBUG][ERS]   glass_sender_count: {glass_sender_count}")

            # Customer feedback count
            customer_feedback_count = feedback_counts['total_feedback']
            print(f"[DEBUG][ERS]   customer_feedback_count: {customer_feedback_count}")

            # Calculate total count
            total_count = (
                branded_frames_count + 
                branded_lenses_count + 
                factory_orders_count + 
                normal_orders_count + 
                customer_feedback_count
            )
            print(f"[DEBUG][ERS]   total_count: {total_count}")

            # Calculate total sales amount for this employee
            total_sales = employee_orders.aggregate(
                total=Sum('total_price')
            )['total'] or 0
            print(f"[DEBUG][ERS]   total_sales: {total_sales}")

            # Get branch info - prioritize from orders created by employee, 
            # then from feedback orders, then from glass issued orders
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
            elif employee_orders.exists():
                first_order_branch = employee_orders.first().branch
                if first_order_branch:
                    branch_info = {
                        'id': first_order_branch.id,
                        'name': first_order_branch.branch_name,
                        'location': first_order_branch.location
                    }
            elif feedback_base_query.exists():
                first_feedback = feedback_base_query.first()
                if first_feedback and first_feedback.order.branch:
                    branch_info = {
                        'id': first_feedback.order.branch.id,
                        'name': first_feedback.order.branch.branch_name,
                        'location': first_feedback.order.branch.location
                    }
            elif glass_sender_base_query.exists():
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
            print(f"[DEBUG][ERS]   Finished employee {idx+1}/{employees.count()} (t={time.time()-t_emp:.3f}s)")
            result.append(employee_data)

        print(f"[DEBUG][ERS] Step 6: Sorting results (t={time.time()-t0:.3f}s)")
        result.sort(key=lambda x: x['total_count'], reverse=True)
        print(f"[DEBUG][ERS] Step 7: Returning result (t={time.time()-t0:.3f}s)")
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