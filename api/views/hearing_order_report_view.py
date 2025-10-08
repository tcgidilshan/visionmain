from re import A
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
        invoice_number = request.query_params.get('invoice_number')
        mobile = request.query_params.get('mobile')
        nic = request.query_params.get('nic')
        patient_name = request.query_params.get('patient_name')  # <-- Add this line
        
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
                is_deleted=False
            )
            
            # Apply branch filter if provided
            if branch_id:
                invoices = invoices.filter(order__branch_id=branch_id)
                
            # Apply search filters
            search_filters = Q()
            if invoice_number:
                search_filters |= Q(invoice_number__icontains=invoice_number)
            if mobile:
                search_filters |= Q(order__customer__phone_number__icontains=mobile)
                search_filters |= Q(order__customer__extra_phone_number__icontains=mobile)
            if nic:
                search_filters |= Q(order__customer__nic__icontains=nic)
            if patient_name:  # <-- Add this block
                search_filters |= Q(order__customer__name__icontains=patient_name)
                
            if search_filters:
                invoices = invoices.filter(search_filters)
            
            # Create a Q object for the next_service_date filterw
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
                
                # Use total_payment from order
                total_paid = float(order.total_payment) if order.total_payment else 0.0
                
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
                        'total_paid': total_paid,
                        'balance': float(order.total_price) - total_paid,
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
                    'last_service_date': last_service.last_service_date.isoformat() if last_service.last_service_date else None,
                    'scheduled_service_date': last_service.scheduled_service_date.isoformat() if last_service.scheduled_service_date else None,
                    'price': float(last_service.price) if last_service.price else 0.0
                }
            return None
        except Exception:
            return None

class HearingOrderReminderReportView(APIView):
    # Pagination
    pagination_class = PaginationService
    
    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        start_date = request.query_params.get("start_date")  # Optional: Format YYYY-MM-DD
        end_date = request.query_params.get("end_date")      # Optional: Format YYYY-MM-DD
        invoice_number = request.query_params.get('invoice_number')
        mobile = request.query_params.get('mobile')
        nic = request.query_params.get('nic')
        
        if not branch_id:
            return Response({"error": "branch_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get current date in the timezone
            today = timezone.now().date()
            
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
                is_deleted=False,
                order__branch_id=branch_id
            )
            
            # Apply search filters
            search_filters = Q()
            if invoice_number:
                search_filters |= Q(invoice_number__icontains=invoice_number)
            if mobile:
                search_filters |= Q(order__customer__phone_number__icontains=mobile)
                search_filters |= Q(order__customer__extra_phone_number__icontains=mobile)
            if nic:
                search_filters |= Q(order__customer__nic__icontains=nic)
                
            if search_filters:
                invoices = invoices.filter(search_filters)
            
            # Create a Q object for the next_service_date filter
            date_filters = Q()
            if start_datetime and end_datetime:
                date_filters &= Q(order__order_items__next_service_date__range=(start_datetime.date(), end_datetime.date()))
            elif start_datetime:
                date_filters &= Q(order__order_items__next_service_date__gte=start_datetime.date())
            elif end_datetime:
                date_filters &= Q(order__order_items__next_service_date__lte=end_datetime.date())
            else:
                # Default: show only overdue services (next_service_date <= today)
                date_filters &= Q(order__order_items__next_service_date__lte=today)
            
            # Apply the date filters
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
                
                # Use total_payment from order
                total_paid = float(order.total_payment) if order.total_payment else 0.0
                
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
                            'days_overdue': (today - item.next_service_date).days if item.next_service_date and item.next_service_date <= today else 0,
                            'serial_no': item.serial_no or '',
                            'battery': item.battery or '',
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
                        'extra_phone_number': order.customer.extra_phone_number or '',
                        'branch_name': order.branch.branch_name,
                        'subtotal': float(order.sub_total),
                        'discount': float(order.discount) if order.discount else 0.0,
                        'total_price': float(order.total_payment),
                        'total_paid': total_paid,
                        'balance': float(order.total_price) - float(order.total_payment),
                        'items': items_data,
                        'order_remark': order.order_remark or ''
                    })
            
            # Return paginated response
            return paginator.get_paginated_response(result)
            
        except ValueError as ve:
            return Response(
                {"error": f"Invalid date format. Please use YYYY-MM-DD format. Error: {str(ve)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_last_service_record(self, order_id):
        """Helper method to get the last service record for an order item"""
        try:
            last_service = HearingOrderItemService.objects.filter(
                order=order_id
            ).order_by('-created_at').first()
            
            if last_service:
                return {
                    'last_service_date': last_service.last_service_date.isoformat() if last_service.last_service_date else None,
                    'scheduled_service_date': last_service.scheduled_service_date.isoformat() if last_service.scheduled_service_date else None,
                    'price': float(last_service.price) if last_service.price else 0.0
                }
            return None
        except Exception:
            return None
class HearingOrderReportByOrderDateView(APIView):
    """
    Same as HearingOrderReportView, but filters by order.order_date instead of next_service_date.
    """
    pagination_class = PaginationService

    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        start_date = request.query_params.get("start_date")  # Format: YYYY-MM-DD
        end_date = request.query_params.get("end_date")  # Format: YYYY-MM-DD
        invoice_number = request.query_params.get('invoice_number')
        mobile = request.query_params.get('mobile')
        nic = request.query_params.get('nic')
        patient_name = request.query_params.get('patient_name')  # <-- Add this line

        if not branch_id:
            return Response({"error": "branch parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_datetime = None
            end_datetime = None
            if start_date:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if end_date:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

            invoices = Invoice.objects.filter(
                invoice_type='hearing',
                is_deleted=False
            )
            if branch_id:
                invoices = invoices.filter(order__branch_id=branch_id)

            search_filters = Q()
            if invoice_number:
                search_filters |= Q(invoice_number__icontains=invoice_number)
            if mobile:
                search_filters |= Q(order__customer__phone_number__icontains=mobile)
                search_filters |= Q(order__customer__extra_phone_number__icontains=mobile)
            if nic:
                search_filters |= Q(order__customer__nic__icontains=nic)
            if patient_name:  # <-- Add this block
                search_filters |= Q(order__customer__name__icontains=patient_name)
            if search_filters:
                invoices = invoices.filter(search_filters)

            # Filter by order_date
            date_filters = Q()
            if start_datetime and end_datetime:
                date_filters &= Q(order__order_date__range=(start_datetime, end_datetime))
            elif start_datetime:
                date_filters &= Q(order__order_date__gte=start_datetime)
            elif end_datetime:
                date_filters &= Q(order__order_date__lte=end_datetime)
            if start_datetime or end_datetime:
                invoices = invoices.filter(date_filters)

            invoices = invoices.select_related(
                'order',
                'order__customer',
                'order__branch'
            ).prefetch_related(
                Prefetch(
                    'order__order_items',
                    queryset=OrderItem.objects.filter(
                        hearing_item__isnull=False
                    ).select_related('hearing_item')
                ),
                Prefetch(
                    'order__orderpayment_set',
                    queryset=OrderPayment.objects.filter(
                        is_deleted=False
                    )
                )
            ).distinct()

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(invoices, request)

            result = []
            for invoice in page:
                order = invoice.order
                order_items = order.order_items.all()
                # Use total_payment from order
                total_paid = float(order.total_payment) if order.total_payment else 0.0
                items_data = []
                for item in order_items:
                    if item.hearing_item:
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
                            'last_service': self._get_last_service_record(order.id)
                        })
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
                        'total_paid': total_paid,
                        'balance': float(order.total_price) - total_paid,
                        'items': items_data,
                        'order_remark': order.order_remark or ''
                    })
            return paginator.get_paginated_response(result)
        except ValueError as ve:
            return Response({"error": f"Invalid date format. Please use YYYY-MM-DD format. Error: {str(ve)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_last_service_record(self, order_id):
        try:
            last_service = HearingOrderItemService.objects.filter(
                order=order_id
            ).order_by('-created_at').first()
            if last_service:
                return {
                    'last_service_date': last_service.last_service_date.isoformat() if last_service.last_service_date else None,
                    'scheduled_service_date': last_service.scheduled_service_date.isoformat() if last_service.scheduled_service_date else None,
                    'price': float(last_service.price) if last_service.price else 0.0
                }
            return None
        except Exception:
            return None