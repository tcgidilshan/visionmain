from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch
from ..models import (
    Invoice, Order, Patient, Refraction, RefractionDetails, 
    OrderItem, OrderPayment, OrderProgress, ArrivalStatus, 
    MntOrder, OrderFeedback, OrderItemWhatsAppLog, Expense,
    CustomUser, Frame, Lens, ExternalLens, PaymentMethodBanks
)
from ..services.time_zone_convert_service import TimezoneConverterService


class InvoiceTrackingReportView(APIView):
    """
    View to generate detailed invoice tracking report for factory orders.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        invoice_number = request.query_params.get('invoice_number')

        # Validate required parameters
        if not branch_id:
            return Response({
                "error": "branch_id is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            branch_id_int = int(branch_id)

            # Build query filter
            filters = {
                'invoice_type': 'factory',
                'order__branch_id': branch_id_int,
                'is_deleted': False
            }

            # If invoice number is provided, search by invoice number only
            if invoice_number and invoice_number.strip():
                filters['invoice_number__icontains'] = invoice_number.strip()
            else:
                # If no invoice number, date range is required
                if not start_date or not end_date:
                    return Response({
                        "error": "start_date and end_date are required when invoice_number is not provided."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Convert dates to timezone-aware datetime
                start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
                filters['invoice_date__gte'] = start_datetime
                filters['invoice_date__lt'] = end_datetime

            # Fetch invoices with related data
            invoices = Invoice.objects.filter(**filters).select_related(
                'order__customer',
                'order__refraction',
                'order__sales_staff_code',
                'order__issued_by'
            ).prefetch_related(
                'order__order_items__frame__brand',
                'order__order_items__frame__code',
                'order__order_items__frame__color',
                'order__order_items__lens__brand',
                'order__order_items__lens__type',
                'order__order_items__lens__coating',
                'order__order_items__external_lens',
                'order__order_items__user',
                'order__order_items__admin',
                'order__order_progress_status',
                'order__arrival_status',
                'order__mnt_orders__user',
                'order__mnt_orders__admin',
                'order__order_feedback__user',
                'order__whatsapp_logs',
                'order__orderpayment_set__user',
                'order__orderpayment_set__admin',
                'order__orderpayment_set__payment_method_bank',
                'order__expense_refunds'
            ).order_by('-invoice_date')

            result = []

            for invoice in invoices:
                order = invoice.order
                customer = order.customer
                refraction = order.refraction

                # Build invoice data structure
                invoice_data = {
                    'invoice_number': invoice.invoice_number,
                    'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                    
                    # Patient Information
                    'patient': {
                        'name': customer.name if customer else None,
                        'nic': customer.nic if customer else None,
                        'mobile': customer.phone_number if customer else None,
                    },
                    
                    # Refraction Information
                    'refraction': self._get_refraction_data(refraction),
                    
                    # Refraction Details
                    'refraction_details': self._get_refraction_details(refraction),
                    
                    # Order Information
                    'order': {
                        'total': float(order.total_price) if order.total_price else 0,
                        'sub_total': float(order.sub_total) if order.sub_total else 0,
                        'total_payment': float(order.total_payment) if order.total_payment else 0,
                        'discount': float(order.discount) if order.discount else 0,
                        'sales_staff': order.sales_staff_code.username if order.sales_staff_code else None,
                        'order_date': order.order_date.isoformat() if order.order_date else None,
                    },
                    
                    # Issued By Information
                    'issued_by': {
                        'user': order.issued_by.username if order.issued_by else None,
                        'issued_date': order.issued_date.isoformat() if order.issued_date else None,
                    },
                    
                    # Fitting Status
                    'fitting_status': {
                        'status': order.fitting_status,
                        'updated_date': order.fitting_status_updated_date.isoformat() if order.fitting_status_updated_date else None,
                    },
                    
                    # Order Feedback
                    'feedback': self._get_order_feedback(order),
                    
                    # Progress Stages
                    'progress_stages': self._get_progress_stages(order),
                    
                    # Arrival Status
                    'arrival_status': self._get_arrival_status(order),
                    
                    # MNT Orders
                    'mnt_orders': self._get_mnt_orders(order),
                    
                    # Order Items
                    'order_items': self._get_order_items(order),
                    
                    # WhatsApp Logs
                    'whatsapp_logs': self._get_whatsapp_logs(order),
                    
                    # Payments
                    'payments': self._get_payments(order),
                    
                    # Refunds
                    'refunds': self._get_refunds(order),
                }
                
                result.append(invoice_data)

            return Response({
                'invoices': result,
                'total_count': len(result)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_refraction_data(self, refraction):
        if not refraction:
            return None
        return {
            'number': refraction.refraction_number,
            'created_at': refraction.created_at.isoformat() if refraction.created_at else None,
        }

    def _get_refraction_details(self, refraction):
        if not refraction:
            return None
        try:
            details = refraction.refraction_details
            return {
                'created_at': details.created_at.isoformat() if details.created_at else None,
                'user': details.user.username if details.user else None,
            }
        except:
            return None

    def _get_order_feedback(self, order):
        feedbacks = order.order_feedback.all()
        return [{
            'user': fb.user.username if fb.user else None,
            'rating': fb.rating,
            'comment': fb.comment,
            'created_at': fb.created_at.isoformat() if fb.created_at else None,
        } for fb in feedbacks]

    def _get_progress_stages(self, order):
        stages = order.order_progress_status.all()
        return [{
            'stage': stage.get_progress_status_display(),
            'changed_at': stage.changed_at.isoformat() if stage.changed_at else None,
        } for stage in stages]

    def _get_arrival_status(self, order):
        statuses = order.arrival_status.all()
        return [{
            'status': status.get_arrival_status_display(),
            'created_at': status.created_at.isoformat() if status.created_at else None,
        } for status in statuses]

    def _get_mnt_orders(self, order):
        mnts = order.mnt_orders.all()
        return [{
            'mnt_number': mnt.mnt_number,
            'price': float(mnt.mnt_price) if mnt.mnt_price else 0,
            'user': mnt.user.username if mnt.user else None,
            'admin': mnt.admin.username if mnt.admin else None,
            'created_at': mnt.created_at.isoformat() if mnt.created_at else None,
        } for mnt in mnts]

    def _get_order_items(self, order):
        items = order.order_items.all()
        result = []
        
        for item in items:
            item_data = {
                'quantity': item.quantity,
                'price_per_unit': float(item.price_per_unit),
                'subtotal': float(item.subtotal),
                'is_refund': item.is_refund,
                'note': item.note,
                'created_at': item.created_at.isoformat() if item.created_at else None,
                'user': item.user.username if item.user else None,
                'admin': item.admin.username if item.admin else None,
            }
            
            # Frame details
            if item.frame:
                item_data['frame'] = {
                    'brand': item.frame.brand.name if item.frame.brand else None,
                    'code': item.frame.code.name if item.frame.code else None,
                    'color': item.frame.color.name if item.frame.color else None,
                    'size': item.frame.size,
                    'price': float(item.frame.price),
                }
            
            # Lens details
            if item.lens:
                item_data['lens'] = {
                    'brand': item.lens.brand.name if item.lens.brand else None,
                    'type': item.lens.type.name if item.lens.type else None,
                    'coating': item.lens.coating.name if item.lens.coating else None,
                    'price': float(item.lens.price),
                }
            
            # External lens details
            if item.external_lens:
                item_data['external_lens'] = {
                    'brand': item.external_lens.brand.name if item.external_lens.brand else None,
                    'coating': item.external_lens.coating.name if item.external_lens.coating else None,
                    'type': item.external_lens.lens_type.name if item.external_lens.lens_type else None,
                    'price': float(item.external_lens.price) if item.external_lens.price else 0,
                }
            
            result.append(item_data)
        
        return result

    def _get_whatsapp_logs(self, order):
        logs = order.whatsapp_logs.all()
        return [{
            'status': log.status,
            'created_at': log.created_at.isoformat() if log.created_at else None,
        } for log in logs]

    def _get_payments(self, order):
        payments = order.orderpayment_set.all()
        result = []
        
        for payment in payments:
            payment_data = {
                'amount': float(payment.amount),
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'payment_method': payment.get_payment_method_display(),
                'is_final_payment': payment.is_final_payment,
                'is_partial': payment.is_partial,
                'is_deleted': payment.is_deleted,
                'deleted_at': payment.deleted_at.isoformat() if payment.deleted_at else None,
                'user': payment.user.username if payment.user else None,
                'admin': payment.admin.username if payment.admin else None,
            }
            
            if payment.payment_method_bank:
                payment_data['bank'] = payment.payment_method_bank.bank_name
            
            result.append(payment_data)
        
        return result

    def _get_refunds(self, order):
        refunds = order.expense_refunds.all()
        return [{
            'amount': float(refund.amount),
            'created_at': refund.created_at.isoformat() if refund.created_at else None,
            'note': refund.note,
        } for refund in refunds]