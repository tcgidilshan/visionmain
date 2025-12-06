#COOrderReportView
from rest_framework.response import Response
from ..services.time_zone_convert_service import TimezoneConverterService
from ..models import Order, OrderPayment, Expense
from rest_framework.views import APIView
from django.db.models import Sum
from ..services.pagination_service import PaginationService



class COOrderReportView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')

        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)

        if not start_datetime or not end_datetime:
            return Response({"error": "Invalid date range"}, status=400)

        # Base queryset filtering CO orders
        co_orders = Order.objects.filter(
            co_order=True,
            order_date__range=(start_datetime, end_datetime)
        ).select_related('customer', 'branch', 'invoice')
        print(co_orders.query)
        if branch_id:
            co_orders = co_orders.filter(branch_id=branch_id)

        data = []
        for order in co_orders:
            # Calculate total payment
            total_payment = OrderPayment.objects.filter(
                order=order, 
                is_deleted=False
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate total expenses
            total_expenses = Expense.objects.filter(
                order_refund=order
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate balance
            balance = float(total_payment) - float(total_expenses)
            
            data.append({
                'id': order.id,
                'order_number': str(order.id),
                'invoice_number': order.invoice.invoice_number if order.invoice else None,
                'customer_name': order.customer.name if order.customer else None,
                'customer_mobile': order.customer.phone_number if order.customer else None,
                'branch_name': order.branch.branch_name if order.branch else None,
                'co_note': order.co_note,
                'co_order': order.co_order,
                'total_amount': float(order.total_price) if order.total_price else 0,
                'total_payment': float(total_payment),
                'total_expenses': float(total_expenses),
                'balance': balance,
                'order_date': order.order_date.isoformat() if order.order_date else None,
            })

        # Calculate summary totals
        total_amount = sum(float(order.total_price) if order.total_price else 0 for order in co_orders)
        total_payment = sum(float(OrderPayment.objects.filter(order=order, is_deleted=False).aggregate(total=Sum('amount'))['total'] or 0) for order in co_orders)
        total_expenses = sum(float(Expense.objects.filter(order_refund=order).aggregate(total=Sum('amount'))['total'] or 0) for order in co_orders)
        total_balance = total_payment - total_expenses

        # Paginate the data
        paginator = PaginationService()
        paginated_data = paginator.paginate_queryset(data, self.request, view=self)

        response_data = {
            'total_co_orders': co_orders.count(),
            'total_amount': total_amount,
            'total_payment': total_payment,
            'total_expenses': total_expenses,
            'total_balance': total_balance,
            'co_orders': paginated_data
        }

        return paginator.get_paginated_response(response_data)