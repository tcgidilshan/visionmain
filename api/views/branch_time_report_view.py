from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from ..models import (
    OrderPayment, ChannelPayment, Expense, OtherIncome, 
    SafeTransaction, SolderingPayment, SolderingInvoice
)
from ..services.pagination_service import PaginationService
from ..services.time_zone_convert_service import TimezoneConverterService


class BranchTimeReportView(APIView):
    """
    GET /api/branch-time-report/?branch_id=1&start_date=2025-12-01&end_date=2025-12-06
    
    Consolidates all financial transactions from different sources into a single time-sorted report.
    """
    
    def get(self, request):
        # Extract and validate parameters
        branch_id = request.query_params.get('branch_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not branch_id:
            return Response(
                {'error': 'branch_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert dates with timezone
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(
            start_date, end_date
        )
        
        if not start_datetime or not end_datetime:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Fetch all transaction types
        order_payments = self.get_order_payments(branch_id, start_datetime, end_datetime)
        channel_payments = self.get_channel_payments(branch_id, start_datetime, end_datetime)
        expenses = self.get_expenses(branch_id, start_datetime, end_datetime)
        other_incomes = self.get_other_incomes(branch_id, start_datetime, end_datetime)
        safe_transactions = self.get_safe_transactions(branch_id, start_datetime, end_datetime)
        soldering_payments = self.get_soldering_payments(branch_id, start_datetime, end_datetime)
        
        # Transform each type
        transformed_orders = [self.transform_order_payment(p) for p in order_payments]
        transformed_channels = [self.transform_channel_payment(p) for p in channel_payments]
        transformed_expenses = [self.transform_expense(e) for e in expenses]
        transformed_incomes = [self.transform_other_income(i) for i in other_incomes]
        transformed_safe = [self.transform_safe_transaction(s) for s in safe_transactions]
        transformed_soldering = [self.transform_soldering_payment(p) for p in soldering_payments]
        
        # Merge and sort
        all_transactions = (
            transformed_orders +
            transformed_channels +
            transformed_expenses +
            transformed_incomes +
            transformed_safe +
            transformed_soldering
        )
        
        # Sort by date_time descending (newest first)
        all_transactions.sort(key=lambda x: x['date_time'], reverse=True)
        
        # Calculate summary
        summary = self.calculate_summary(branch_id, start_datetime, end_datetime)
        summary['transaction_count'] = len(all_transactions)
        
        # Paginate
        paginator = PaginationService()
        paginated_transactions = paginator.paginate_queryset(all_transactions, request)
        
        response_data = {
            'summary': summary,
            'transactions': paginated_transactions if paginated_transactions is not None else all_transactions
        }
        
        if paginated_transactions is not None:
            return paginator.get_paginated_response(response_data)
        
        return Response(response_data)
    
    # Query Methods
    def get_order_payments(self, branch_id, start_date, end_date):
        return OrderPayment.objects.filter(
            is_deleted=False,
            order__branch_id=branch_id,
            payment_date__gte=start_date,
            payment_date__lte=end_date
        ).select_related(
            'order', 'order__invoice', 'order__customer'
        ).values(
            'id', 'payment_date', 'amount', 'payment_method',
            'order__id', 'order__total_price',
            'order__invoice__invoice_number', 'order__customer__name'
        )
    
    def get_channel_payments(self, branch_id, start_date, end_date):
        return ChannelPayment.objects.filter(
            is_deleted=False,
            appointment__branch_id=branch_id,
            payment_date__gte=start_date,
            payment_date__lte=end_date
        ).select_related(
            'appointment', 'appointment__patient', 'appointment__doctor'
        ).values(
            'id', 'payment_date', 'amount', 'payment_method',
            'appointment__id', 'appointment__channel_no', 'appointment__invoice_number',
            'appointment__patient__name', 'appointment__doctor__name'
        )
    
    def get_expenses(self, branch_id, start_date, end_date):
        return Expense.objects.filter(
            branch_id=branch_id,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related('main_category', 'sub_category').values(
            'id', 'created_at', 'amount', 'paid_source',
            'main_category__name', 'sub_category__name',
            'note', 'paid_from_safe', 'is_refund'
        )
    
    def get_other_incomes(self, branch_id, start_date, end_date):
        return OtherIncome.objects.filter(
            branch_id=branch_id,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related('category').values(
            'id', 'created_at', 'amount', 'category__name', 'note'
        )
    
    def get_safe_transactions(self, branch_id, start_date, end_date):
        return SafeTransaction.objects.filter(
            branch_id=branch_id,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).values(
            'id', 'created_at', 'transaction_type', 'amount',
            'reason', 'bank_deposit_id', 'expense_id'
        )
    
    def get_soldering_payments(self, branch_id, start_date, end_date):
        payments = SolderingPayment.objects.filter(
            is_deleted=False,
            order__branch_id=branch_id,
            payment_date__gte=start_date,
            payment_date__lte=end_date
        ).select_related('order', 'order__patient').values(
            'id', 'payment_date', 'amount', 'payment_method',
            'is_final_payment', 'order__id', 'order__patient__name'
        )
        
        result = []
        for payment in payments:
            payment_dict = dict(payment)
            invoice = SolderingInvoice.objects.filter(
                order_id=payment['order__id'], is_deleted=False
            ).values('invoice_number').first()
            payment_dict['invoice_number'] = invoice['invoice_number'] if invoice else None
            result.append(payment_dict)
        
        return result
    
    # Transformation Methods
    def transform_order_payment(self, payment):
        return {
            'transaction_type': 'order_payment',
            'date_time': payment['payment_date'].isoformat() if payment['payment_date'] else None,
            'amount': str(payment['amount']),
            'reference_number': payment['order__invoice__invoice_number'],
            'customer_name': payment['order__customer__name'],
            'payment_method': payment['payment_method'],
            'main_category_name': None,
            'sub_category_name': None,
            'channel_no': None,
            'transaction_subtype': None,
            'additional_info': {
                'order_total': str(payment['order__total_price']),
                'order_id': payment['order__id']
            }
        }
    
    def transform_channel_payment(self, payment):
        return {
            'transaction_type': 'channel_payment',
            'date_time': payment['payment_date'].isoformat() if payment['payment_date'] else None,
            'amount': str(payment['amount']),
            'reference_number': str(payment['appointment__invoice_number']) if payment['appointment__invoice_number'] else None,
            'customer_name': payment['appointment__patient__name'],
            'payment_method': payment['payment_method'],
            'main_category_name': None,
            'sub_category_name': None,
            'channel_no': payment['appointment__channel_no'],
            'transaction_subtype': None,
            'additional_info': {
                'doctor_name': payment['appointment__doctor__name'],
                'appointment_id': payment['appointment__id']
            }
        }
    
    def transform_expense(self, expense):
        return {
            'transaction_type': 'expense',
            'date_time': expense['created_at'].isoformat() if expense['created_at'] else None,
            'amount': str(expense['amount']),
            'reference_number': None,
            'customer_name': None,
            'payment_method': expense['paid_source'],
            'main_category_name': expense['main_category__name'],
            'sub_category_name': expense['sub_category__name'],
            'channel_no': None,
            'transaction_subtype': 'refund' if expense['is_refund'] else None,
            'additional_info': {
                'note': expense['note'],
                'paid_from_safe': expense['paid_from_safe']
            }
        }
    
    def transform_other_income(self, income):
        return {
            'transaction_type': 'other_income',
            'date_time': income['created_at'].isoformat() if income['created_at'] else None,
            'amount': str(income['amount']),
            'reference_number': None,
            'customer_name': None,
            'payment_method': None,
            'main_category_name': income['category__name'],
            'sub_category_name': None,
            'channel_no': None,
            'transaction_subtype': None,
            'additional_info': {'note': income['note']}
        }
    
    def transform_safe_transaction(self, transaction):
        return {
            'transaction_type': 'safe_transaction',
            'date_time': transaction['created_at'].isoformat() if transaction['created_at'] else None,
            'amount': str(transaction['amount']),
            'reference_number': None,
            'customer_name': None,
            'payment_method': None,
            'main_category_name': None,
            'sub_category_name': None,
            'channel_no': None,
            'transaction_subtype': transaction['transaction_type'],
            'additional_info': {
                'reason': transaction['reason'],
                'bank_deposit_id': transaction['bank_deposit_id'],
                'expense_id': transaction['expense_id']
            }
        }
    
    def transform_soldering_payment(self, payment):
        return {
            'transaction_type': 'soldering_payment',
            'date_time': payment['payment_date'].isoformat() if payment['payment_date'] else None,
            'amount': str(payment['amount']),
            'reference_number': payment.get('invoice_number'),
            'customer_name': payment['order__patient__name'],
            'payment_method': payment['payment_method'],
            'main_category_name': None,
            'sub_category_name': None,
            'channel_no': None,
            'transaction_subtype': None,
            'additional_info': {
                'order_id': payment['order__id'],
                'is_final_payment': payment['is_final_payment']
            }
        }
    
    def calculate_summary(self, branch_id, start_date, end_date):
        order_total = OrderPayment.objects.filter(
            is_deleted=False, order__branch_id=branch_id,
            payment_date__gte=start_date, payment_date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        channel_total = ChannelPayment.objects.filter(
            is_deleted=False, appointment__branch_id=branch_id,
            payment_date__gte=start_date, payment_date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        soldering_total = SolderingPayment.objects.filter(
            is_deleted=False, order__branch_id=branch_id,
            payment_date__gte=start_date, payment_date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        income_total = OtherIncome.objects.filter(
            branch_id=branch_id,
            created_at__gte=start_date, created_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expense_total = Expense.objects.filter(
            branch_id=branch_id,
            created_at__gte=start_date, created_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        bank_deposit_total = SafeTransaction.objects.filter(
            branch_id=branch_id, transaction_type='deposit',
            created_at__gte=start_date, created_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'total_received': str(order_total + channel_total + soldering_total + income_total),
            'total_expenses': str(expense_total),
            'total_bank_deposits': str(bank_deposit_total),
        }