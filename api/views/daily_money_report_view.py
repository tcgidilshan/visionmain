from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from api.models import (
    Branch, Order, OrderPayment, Invoice, Appointment, ChannelPayment, 
    SolderingOrder, SolderingPayment, Expense, OtherIncome, BankDeposit,
    SafeTransaction, CustomUser, MntOrder
)
from api.services.time_zone_convert_service import TimezoneConverterService


class DailyMoneyReportView(APIView):
    """
    Comprehensive daily money report showing all financial transactions by branch
    Includes: Factory orders, Normal orders, Frame only orders, Hearing orders,
    Channel payments, Soldering orders, Expenses, Banking, Safe transactions, Other income
    """
    
    def post(self, request):
        """
        POST endpoint to get daily money report with date and branch filtering
        Request body: {
            "date": "YYYY-MM-DD",
            "branch_id": integer (optional, if not provided returns all branches)
        }
        """
        try:
            # Get request data
            date_str = request.data.get('date')
            branch_id = request.data.get('branch_id')
            
            if not date_str:
                return Response({
                    "error": "Date is required in format YYYY-MM-DD"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse and validate date
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    "error": "Invalid date format. Use YYYY-MM-DD"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create timezone-aware datetime range for the day
            day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
            
            # Filter branches
            if branch_id:
                try:
                    branches = Branch.objects.filter(id=branch_id)
                    if not branches.exists():
                        return Response({
                            "error": "Branch not found"
                        }, status=status.HTTP_404_NOT_FOUND)
                except ValueError:
                    return Response({
                        "error": "Invalid branch_id"
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                branches = Branch.objects.all()
            
            # Collect all transactions in a flat list
            all_transactions = []
            total_income = 0
            total_expenses = 0
            
            for branch in branches:
                branch_transactions = self._get_all_branch_transactions_flat(branch, day_start, day_end, target_date)
                # Add branch info to each transaction
                for transaction in branch_transactions["transactions"]:
                    transaction["branch_name"] = branch.branch_name
                    transaction["branch_id"] = branch.id
                all_transactions.extend(branch_transactions["transactions"])
                total_income += branch_transactions["total_income"]
                total_expenses += branch_transactions["total_expenses"]
            
            # Sort transactions by time (most recent first)
            all_transactions.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
            
            report_data = {
                "date": date_str,
                "transactions": all_transactions,
                "summary": {
                    "total_income": total_income,
                    "total_expenses": total_expenses,
                    "net_amount": total_income - total_expenses,
                    "total_transactions": len(all_transactions)
                }
            }
            
            return Response(report_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_all_branch_transactions_flat(self, branch, day_start, day_end, target_date):
        """Get all transactions for a specific branch in a flat list format matching the table structure"""
        all_transactions = []
        total_income = 0
        total_expenses = 0
        
        # Get all transaction types
        factory_data = self._get_factory_orders_flat(branch, day_start, day_end)
        normal_data = self._get_normal_orders_flat(branch, day_start, day_end)
        frame_data = self._get_frame_only_orders_flat(branch, day_start, day_end)
        hearing_data = self._get_hearing_orders_flat(branch, day_start, day_end)
        channel_data = self._get_channel_payments_flat(branch, day_start, day_end)
        soldering_data = self._get_soldering_orders_flat(branch, day_start, day_end)
        safe_expenses_data = self._get_expenses_flat(branch, target_date, 'safe')
        cashier_expenses_data = self._get_expenses_flat(branch, target_date, 'cashier')
        banking_data = self._get_banking_transactions_flat(branch, target_date)
        safe_transactions_data = self._get_safe_transactions_flat(branch, target_date)
        other_income_data = self._get_other_income_flat(branch, target_date)
        
        # Combine all transactions
        all_transactions.extend(factory_data["transactions"])
        all_transactions.extend(normal_data["transactions"])
        all_transactions.extend(frame_data["transactions"])
        all_transactions.extend(hearing_data["transactions"])
        all_transactions.extend(channel_data["transactions"])
        all_transactions.extend(soldering_data["transactions"])
        all_transactions.extend(safe_expenses_data["transactions"])
        all_transactions.extend(cashier_expenses_data["transactions"])
        all_transactions.extend(banking_data["transactions"])
        all_transactions.extend(safe_transactions_data["transactions"])
        all_transactions.extend(other_income_data["transactions"])
        
        # Calculate totals
        total_income = (factory_data["total"] + normal_data["total"] + frame_data["total"] + 
                       hearing_data["total"] + channel_data["total"] + soldering_data["total"] + 
                       banking_data["total"] + other_income_data["total"])
        
        total_expenses = (safe_expenses_data["total"] + cashier_expenses_data["total"])
        
        # Add safe transaction amounts (can be positive or negative)
        total_income += max(0, safe_transactions_data["total"])
        total_expenses += abs(min(0, safe_transactions_data["total"]))
        
        return {
            "transactions": all_transactions,
            "total_income": total_income,
            "total_expenses": total_expenses
        }
    
    # Flat transaction methods for table format
    def _get_factory_orders_flat(self, branch, day_start, day_end):
        """Get factory orders in flat table format"""
        transactions = []
        total = 0
        
        factory_invoices = Invoice.objects.filter(
            order__branch=branch,
            invoice_type='factory',
            invoice_date__range=(day_start, day_end),
            is_deleted=False
        ).select_related('order', 'order__customer')
        
        for invoice in factory_invoices:
            payments = OrderPayment.objects.filter(
                order=invoice.order,
                payment_date__range=(day_start, day_end),
                is_deleted=False,
                transaction_status='success'
            )
            
            for payment in payments:
                special_indicator = self._get_special_indicator(payment.is_edited, payment.is_partial, payment.order.is_refund)
                
                transactions.append({
                    "date": payment.payment_date.strftime('%d/%m/%Y'),
                    "time": payment.payment_date.strftime('%I.%M%p'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "-",
                    "form_name": "Factory order",
                    "remark": payment.order.order_remark or "-",
                    "type": "Save" if not payment.is_edited else "Update",
                    "special": special_indicator,
                    "amount": f"Rs. {int(payment.amount)}"
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_normal_orders_flat(self, branch, day_start, day_end):
        """Get normal orders in flat table format"""
        transactions = []
        total = 0
        
        normal_invoices = Invoice.objects.filter(
            order__branch=branch,
            invoice_type='normal',
            invoice_date__range=(day_start, day_end),
            is_deleted=False
        ).select_related('order', 'order__customer')
        
        for invoice in normal_invoices:
            payments = OrderPayment.objects.filter(
                order=invoice.order,
                payment_date__range=(day_start, day_end),
                is_deleted=False,
                transaction_status='success'
            )
            
            for payment in payments:
                special_indicator = self._get_special_indicator(payment.is_edited, payment.is_partial, payment.order.is_refund)
                
                transactions.append({
                    "date": payment.payment_date.strftime('%d/%m/%Y'),
                    "time": payment.payment_date.strftime('%I.%M%p'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "-",
                    "form_name": "Normal order",
                    "remark": payment.order.order_remark or "-",
                    "type": "Save" if not payment.is_edited else "Update",
                    "special": special_indicator,
                    "amount": f"Rs. {int(payment.amount)}"
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_frame_only_orders_flat(self, branch, day_start, day_end):
        """Get frame only orders in flat table format"""
        transactions = []
        total = 0
        
        frame_orders = Order.objects.filter(
            branch=branch,
            is_frame_only=True,
            order_date__range=(day_start, day_end),
            is_deleted=False
        ).select_related('customer')
        
        for order in frame_orders:
            payments = OrderPayment.objects.filter(
                order=order,
                payment_date__range=(day_start, day_end),
                is_deleted=False,
                transaction_status='success'
            )
            
            for payment in payments:
                special_indicator = self._get_special_indicator(payment.is_edited, payment.is_partial, payment.order.is_refund)
                
                transactions.append({
                    "date": payment.payment_date.strftime('%d/%m/%Y'),
                    "time": payment.payment_date.strftime('%I.%M%p'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "-",
                    "form_name": "Frame only order",
                    "remark": payment.order.order_remark or "-",
                    "type": "Save" if not payment.is_edited else "Update",
                    "special": special_indicator,
                    "amount": f"Rs. {int(payment.amount)}"
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_hearing_orders_flat(self, branch, day_start, day_end):
        """Get hearing orders in flat table format"""
        transactions = []
        total = 0
        
        hearing_invoices = Invoice.objects.filter(
            order__branch=branch,
            invoice_type='hearing',
            invoice_date__range=(day_start, day_end),
            is_deleted=False
        ).select_related('order', 'order__customer')
        
        for invoice in hearing_invoices:
            payments = OrderPayment.objects.filter(
                order=invoice.order,
                payment_date__range=(day_start, day_end),
                is_deleted=False,
                transaction_status='success'
            )
            
            for payment in payments:
                special_indicator = self._get_special_indicator(payment.is_edited, payment.is_partial, payment.order.is_refund)
                
                transactions.append({
                    "date": payment.payment_date.strftime('%d/%m/%Y'),
                    "time": payment.payment_date.strftime('%I.%M%p'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "-",
                    "form_name": "Hearing order",
                    "remark": payment.order.order_remark or "-",
                    "type": "Save" if not payment.is_edited else "Update",
                    "special": special_indicator,
                    "amount": f"Rs. {int(payment.amount)}"
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_channel_payments_flat(self, branch, day_start, day_end):
        """Get channel payments in flat table format"""
        transactions = []
        total = 0
        
        channel_payments = ChannelPayment.objects.filter(
            appointment__branch=branch,
            payment_date__range=(day_start, day_end),
            is_deleted=False
        ).select_related('appointment', 'appointment__patient', 'appointment__doctor')
        
        for payment in channel_payments:
            special_indicator = self._get_special_indicator(payment.is_edited, not payment.is_final, payment.appointment.is_refund)
            
            transactions.append({
                "date": payment.payment_date.strftime('%d/%m/%Y'),
                "time": payment.payment_date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Channel",
                "remark": payment.appointment.note or "-",
                "type": "Save" if not payment.is_edited else "Update",
                "special": special_indicator,
                "amount": f"Rs. {int(payment.amount)}"
            })
            total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_soldering_orders_flat(self, branch, day_start, day_end):
        """Get soldering orders in flat table format"""
        transactions = []
        total = 0
        
        soldering_payments = SolderingPayment.objects.filter(
            order__branch=branch,
            payment_date__range=(day_start, day_end),
            is_deleted=False,
            transaction_status='completed'
        ).select_related('order', 'order__patient')
        
        for payment in soldering_payments:
            special_indicator = self._get_special_indicator(False, payment.is_partial, payment.transaction_status == 'refunded')
            
            transactions.append({
                "date": payment.payment_date.strftime('%d/%m/%Y'),
                "time": payment.payment_date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Soldering",
                "remark": payment.order.note or "-",
                "type": "Save",
                "special": special_indicator,
                "amount": f"Rs. {int(payment.amount)}"
            })
            total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_expenses_flat(self, branch, target_date, source_type):
        """Get expenses in flat table format"""
        transactions = []
        total = 0
        
        expenses = Expense.objects.filter(
            branch=branch,
            created_at__date=target_date,
            paid_source=source_type
        ).select_related('main_category', 'sub_category')
        
        for expense in expenses:
            source_name = "Safe" if source_type == 'safe' else "Cashier"
            special_indicator = self._get_special_indicator(False, False, expense.is_refund)
            
            transactions.append({
                "date": expense.created_at.strftime('%d/%m/%Y'),
                "time": expense.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": source_name,
                "remark": expense.note or "-",
                "type": "Expense",
                "special": special_indicator,
                "amount": f"Rs. {int(expense.amount)}"
            })
            total += float(expense.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_banking_transactions_flat(self, branch, target_date):
        """Get banking transactions in flat table format"""
        transactions = []
        total = 0
        
        deposits = BankDeposit.objects.filter(
            branch=branch,
            date=target_date
        ).select_related('bank_account')
        
        for deposit in deposits:
            special_indicator = True if deposit.is_confirmed else False
            
            transactions.append({
                "date": deposit.date.strftime('%d/%m/%Y'),
                "time": "-",
                "user_name": "-",
                "form_name": "Banking",
                "remark": deposit.note or "-",
                "type": "Deposit",
                "special": special_indicator,
                "amount": f"Rs. {int(deposit.amount)}"
            })
            total += float(deposit.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_safe_transactions_flat(self, branch, target_date):
        """Get safe transactions in flat table format"""
        transactions = []
        total = 0
        
        safe_transactions = SafeTransaction.objects.filter(
            branch=branch,
            date=target_date
        )
        
        for transaction in safe_transactions:
            amount = float(transaction.amount)
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": False,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        # Create timezone-aware datetime range for the day
        day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__range=(day_start, day_end)
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": False,
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return True  # Special transaction - refund
        elif is_edited or is_partial:
            return True  # Special transaction - edited/partial
        else:
            return False  # Normal transaction
