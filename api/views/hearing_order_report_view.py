from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Sum, F
from django.utils import timezone
from django.db.models import Prefetch
from datetime import datetime
from ..models import Invoice, OrderItem, OrderPayment, HearingOrderItemService
from ..serializers import HearingOrderItemServiceSerializer
from ..services.pagination_service import PaginationService

class HearingOrderReportView(APIView):
    # Pagination
    pagination_class = PaginationService
    
    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        start_date = request.query_params.get("start_date")  # Format: YYYY-MM-DD
        end_date = request.query_params.get("end_date")  # Format: YYYY-MM-DD
        
        if not branch_id:
            return Response({"error": "branch parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Convert string dates to datetime objects if provided
            start_datetime = None
            end_datetime = None
            
            if start_date:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc) 
            if end_date:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

            # Base query for hearing invoices
            invoices = Invoice.objects.filter(
                invoice_type='hearing',
                order__branch_id=branch_id,
                is_deleted=False
            )
            
            # Create a Q object for the next_service_date filter
            date_filters = Q()
            if start_datetime and end_datetime:
                date_filters &= Q(order__order_items__next_service_date__range=(start_datetime.date(), end_datetime.date()))
            elif start_datetime:
                date_filters &= Q(order__order_items__next_service_date__gte=start_datetime.date())
            elif end_datetime:
                date_filters &= Q(order__order_items__next_service_date__lte=end_datetime.date())
            
            # Apply the date filters if any date range was provided
            if start_datetime or end_datetime:
                invoices = invoices.filter(date_filters)
            
            # Prefetch related data to optimize queries
            invoices = invoices.select_related(
                'order',
                'order__customer',
                'order__branch'
            ).prefetch_related(
                Prefetch(
                    'order__order_items',
                    queryset=OrderItem.objects.filter(
                        hearing_item__isnull=False  # Only include order items with hearing items
                    ).select_related('hearing_item')
                ),
                Prefetch(
                    'order__orderpayment_set',
                    queryset=OrderPayment.objects.filter(
                        is_deleted=False
                    )
                )
            ).distinct()  # Add distinct to avoid duplicate invoices
            
            # Paginate the queryset
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(invoices, request)
            
            # Prepare response data
            result = []
            for invoice in page:
                order = invoice.order
                order_items = order.order_items.all()
                
                # Calculate total payments for this order
                total_payments = sum(
                    payment.amount 
                    for payment in order.orderpayment_set.all()
                    if not payment.is_deleted
                )
                
                # Filter items based on date range if dates were provided
                items_data = []
                for item in order_items:
                    if item.hearing_item:
                        # Skip items that don't match the date range if dates were provided
                        if (start_datetime and item.next_service_date and 
                            item.next_service_date < start_datetime.date()):
                            continue
                        if (end_datetime and item.next_service_date and 
                            item.next_service_date > end_datetime.date()):
                            continue
                            
                        items_data.append({
                            'order_item_id': item.id,
                            'hearing_item_id': item.hearing_item.id,
                            'item_name': item.hearing_item.name,
                            'quantity': item.quantity,
                            'price_per_unit': float(item.price_per_unit),
                            'subtotal': float(item.subtotal),
                            'last_reminder_at': item.last_reminder_at.isoformat() if item.last_reminder_at else None,
                            'next_service_date': item.next_service_date.isoformat() if item.next_service_date else None,
                            'serial_no': item.serial_no,
                            'battery': item.battery,
                            'note': item.note or '',
                            'last_service': self._get_last_service_record(order.id)  # Add last service record
                        })
                
                # Only add invoice to result if it has matching items
                if items_data:
                    result.append({
                        'invoice_number': invoice.invoice_number,
                        'invoice_date': invoice.invoice_date.isoformat(),
                        'order_id': order.id,
                        'customer_name': f"{order.customer.name}",
                        'customer_phone': order.customer.phone_number,
                        'extra_phone_number': order.customer.extra_phone_number,
                        'branch_name': order.branch.branch_name,
                        'subtotal': float(order.sub_total),
                        'discount': float(order.discount) if order.discount else 0.0,
                        'total_price': float(order.total_price),
                        'total_paid': float(total_payments),
                        'balance': float(order.total_price - total_payments),
                        'items': items_data,
                        'order_remark': order.order_remark or ''
                    })
            
            # Return paginated response
            return paginator.get_paginated_response(result)
            
        except ValueError as ve:
            return Response({"error": f"Invalid date format. Please use YYYY-MM-DD format. Error: {str(ve)}"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_last_service_record(self, order_id):
        """Helper method to get the last service record for an order item"""
        try:
            last_service = HearingOrderItemService.objects.filter(
                order=order_id
            ).order_by('-created_at').first()
            
            if last_service:
                return {
                    'last_service_date': last_service.last_service_date.isoformat(),
                    'scheduled_service_date': last_service.scheduled_service_date.isoformat(),
                    'price': float(last_service.price)
                }
            return None
        except Exception:
            return None