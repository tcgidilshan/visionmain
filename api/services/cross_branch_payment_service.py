from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from ..models import OrderPayment, Invoice
from .time_zone_convert_service import TimezoneConverterService


class CrossBranchPaymentService:
    """
    Service to generate cross-branch payment reports.
    Filters payments by branch and invoice type with date range.
    """

    @staticmethod
    def get_cross_branch_payment_report(branch_id, start_date=None, end_date=None):
        """
        Get payment report for a specific branch.
        
        Args:
            branch_id (int): Branch ID where payment was received
            start_date (str): Start date in format 'YYYY-MM-DD' (optional)
            end_date (str): End date in format 'YYYY-MM-DD' (optional)
            
        Returns:
            dict: Report data with payments and summary
        """
        try:
            # Convert dates to timezone-aware datetime objects
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(
                start_date, end_date
            )
            
            # Base queryset: payments for this branch, not deleted
            payments_query = OrderPayment.objects.filter(
                paid_branch_id=branch_id,
                is_deleted=False
            ).select_related(
                'order',
                'order__invoice',
                'user',
                'admin',
                'payment_method_bank'
            )
            
            # Filter by invoice type = 'factory'
            payments_query = payments_query.filter(
                order__invoice__invoice_type='factory'
            )
            
            # Filter by date range if provided
            if start_datetime and end_datetime:
                payments_query = payments_query.filter(
                    payment_date__range=(start_datetime, end_datetime)
                )
            
            # Get payment details
            payments = payments_query.order_by('-payment_date')
            
            payment_details = []
            for payment in payments:
                payment_details.append({
                    'id': payment.id,
                    'order_id': payment.order.id,
                    'invoice_number': payment.order.invoice.invoice_number if payment.order.invoice else 'N/A',
                    'invoice_type': payment.order.invoice.invoice_type if payment.order.invoice else 'N/A',
                    'amount': float(payment.amount),
                    'payment_method': payment.get_payment_method_display(),
                    'transaction_status': payment.get_transaction_status_display(),
                    'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                    'is_final_payment': payment.is_final_payment,
                    'user': payment.user.username if payment.user else None,
                    'admin': payment.admin.username if payment.admin else None,
                    'payment_method_bank': payment.payment_method_bank.name if payment.payment_method_bank else None,
                })
            
            # Calculate summary
            total_payment = payments_query.aggregate(
                total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
            )['total']
            
            payment_count = payments_query.count()
            
            # Calculate payment method wise totals
            total_cash = payments_query.filter(
                payment_method='cash'
            ).aggregate(
                total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
            )['total']
            
            total_online_transfer = payments_query.filter(
                payment_method='online_transfer'
            ).aggregate(
                total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
            )['total']
            
            # Get credit card payments breakdown by bank
            credit_card_payments = payments_query.filter(
                payment_method='credit_card'
            )
            
            total_credit_card = credit_card_payments.aggregate(
                total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
            )['total']
            
            # Breakdown credit card by bank
            credit_card_by_bank = {}
            for payment in credit_card_payments.select_related('payment_method_bank'):
                bank_name = payment.payment_method_bank.name if payment.payment_method_bank else 'Unknown'
                if bank_name not in credit_card_by_bank:
                    credit_card_by_bank[bank_name] = 0
                credit_card_by_bank[bank_name] += float(payment.amount)
            
            return {
                'status': 'success',
                'branch_id': branch_id,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date,
                },
                'summary': {
                    'total_payment': float(total_payment),
                    'payment_count': payment_count,
                    'invoice_type': 'factory',
                    'total_cash_payment': float(total_cash),
                    'total_credit_card_payment': float(total_credit_card),
                    'total_credit_card_by_bank': credit_card_by_bank,
                    'total_online_transfer_payment': float(total_online_transfer)
                },
                'payments': payment_details
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
