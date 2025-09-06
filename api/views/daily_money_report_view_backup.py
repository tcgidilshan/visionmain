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
        
        # 1. Factory Orders
        factory_data = self._get_factory_orders_flat(branch, day_start, day_end)
        all_transactions.extend(factory_data["transactions"])
        total_income += factory_data["total"]
        
        # 2. Normal Orders
        normal_data = self._get_normal_orders_flat(branch, day_start, day_end)
        all_transactions.extend(normal_data["transactions"])
        total_income += normal_data["total"]
        
        # 3. Frame Only Orders
        frame_data = self._get_frame_only_orders_flat(branch, day_start, day_end)
        all_transactions.extend(frame_data["transactions"])
        total_income += frame_data["total"]
        
        # 4. Hearing Orders
        hearing_data = self._get_hearing_orders_flat(branch, day_start, day_end)
        all_transactions.extend(hearing_data["transactions"])
        total_income += hearing_data["total"]
        
        # 5. Channel Payments
        channel_data = self._get_channel_payments_flat(branch, day_start, day_end)
        all_transactions.extend(channel_data["transactions"])
        total_income += channel_data["total"]
        
        # 6. Soldering Orders
        soldering_data = self._get_soldering_orders_flat(branch, day_start, day_end)
        all_transactions.extend(soldering_data["transactions"])
        total_income += soldering_data["total"]
        
        # 7. Safe Expenses
        safe_expenses_data = self._get_expenses_flat(branch, target_date, 'safe')
        all_transactions.extend(safe_expenses_data["transactions"])
        total_expenses += safe_expenses_data["total"]
        
        # 8. Cashier Expenses
        cashier_expenses_data = self._get_expenses_flat(branch, target_date, 'cash')
        all_transactions.extend(cashier_expenses_data["transactions"])
        total_expenses += cashier_expenses_data["total"]
        
        # 9. Banking
        banking_data = self._get_banking_transactions_flat(branch, target_date)
        all_transactions.extend(banking_data["transactions"])
        
        # 10. Safe Transactions
        safe_trans_data = self._get_safe_transactions_flat(branch, target_date)
        all_transactions.extend(safe_trans_data["transactions"])
        
        # 11. Other Income
        other_income_data = self._get_other_income_flat(branch, target_date)
        all_transactions.extend(other_income_data["transactions"])
        total_income += other_income_data["total"]
        
        return {
            "transactions": all_transactions,
            "total_income": total_income,
            "total_expenses": total_expenses
        }
    
    def _get_branch_transactions(self, branch, day_start, day_end, target_date):
        """Get all transactions for a specific branch on the target date"""
        
        branch_data = {
            "branch_id": branch.id,
            "branch_name": branch.branch_name,
            "transactions": {
                "factory_orders": [],
                "normal_orders": [],
                "frame_only_orders": [],
                "hearing_orders": [],
                "channel_payments": [],
                "soldering_orders": [],
                "expenses_safe": [],
                "expenses_cashier": [],
                "banking": [],
                "safe_transactions": [],
                "other_income": []
            },
            "totals": {
                "factory_orders": 0,
                "normal_orders": 0,
                "frame_only_orders": 0,
                "hearing_orders": 0,
                "channel_payments": 0,
                "soldering_orders": 0,
                "expenses_safe": 0,
                "expenses_cashier": 0,
                "banking": 0,
                "safe_transactions": 0,
                "other_income": 0,
                "total_income": 0,
                "total_expenses": 0
            }
        }
        
        # 1. Factory Orders (orders with refraction/invoice_type='factory')
        factory_orders = self._get_factory_orders(branch, day_start, day_end)
        branch_data["transactions"]["factory_orders"] = factory_orders["transactions"]
        branch_data["totals"]["factory_orders"] = factory_orders["total"]
        
        # 2. Normal Orders (invoice_type='normal')
        normal_orders = self._get_normal_orders(branch, day_start, day_end)
        branch_data["transactions"]["normal_orders"] = normal_orders["transactions"]
        branch_data["totals"]["normal_orders"] = normal_orders["total"]
        
        # 3. Frame Only Orders (is_frame_only=True)
        frame_only_orders = self._get_frame_only_orders(branch, day_start, day_end)
        branch_data["transactions"]["frame_only_orders"] = frame_only_orders["transactions"]
        branch_data["totals"]["frame_only_orders"] = frame_only_orders["total"]
        
        # 4. Hearing Orders (invoice_type='hearing')
        hearing_orders = self._get_hearing_orders(branch, day_start, day_end)
        branch_data["transactions"]["hearing_orders"] = hearing_orders["transactions"]
        branch_data["totals"]["hearing_orders"] = hearing_orders["total"]
        
        # 5. Channel Payments (appointments)
        channel_payments = self._get_channel_payments(branch, day_start, day_end)
        branch_data["transactions"]["channel_payments"] = channel_payments["transactions"]
        branch_data["totals"]["channel_payments"] = channel_payments["total"]
        
        # 6. Soldering Orders
        soldering_orders = self._get_soldering_orders(branch, day_start, day_end)
        branch_data["transactions"]["soldering_orders"] = soldering_orders["transactions"]
        branch_data["totals"]["soldering_orders"] = soldering_orders["total"]
        
        # 7. Expenses - Safe
        expenses_safe = self._get_expenses(branch, target_date, 'safe')
        branch_data["transactions"]["expenses_safe"] = expenses_safe["transactions"]
        branch_data["totals"]["expenses_safe"] = expenses_safe["total"]
        
        # 8. Expenses - Cashier
        expenses_cashier = self._get_expenses(branch, target_date, 'cash')
        branch_data["transactions"]["expenses_cashier"] = expenses_cashier["transactions"]
        branch_data["totals"]["expenses_cashier"] = expenses_cashier["total"]
        
        # 9. Banking (deposits)
        banking = self._get_banking_transactions(branch, target_date)
        branch_data["transactions"]["banking"] = banking["transactions"]
        branch_data["totals"]["banking"] = banking["total"]
        
        # 10. Safe Transactions
        safe_transactions = self._get_safe_transactions(branch, target_date)
        branch_data["transactions"]["safe_transactions"] = safe_transactions["transactions"]
        branch_data["totals"]["safe_transactions"] = safe_transactions["total"]
        
        # 11. Other Income
        other_income = self._get_other_income(branch, target_date)
        branch_data["transactions"]["other_income"] = other_income["transactions"]
        branch_data["totals"]["other_income"] = other_income["total"]
        
        # Calculate totals
        income_categories = ["factory_orders", "normal_orders", "frame_only_orders", 
                           "hearing_orders", "channel_payments", "soldering_orders", 
                           "other_income"]
        expense_categories = ["expenses_safe", "expenses_cashier"]
        
        branch_data["totals"]["total_income"] = sum(
            branch_data["totals"][cat] for cat in income_categories
        )
        branch_data["totals"]["total_expenses"] = sum(
            branch_data["totals"][cat] for cat in expense_categories
        )
        
        return branch_data
    
    def _get_factory_orders(self, branch, day_start, day_end):
        """Get factory orders (orders with invoice_type='factory')"""
        transactions = []
        total = 0
        
        # Get factory invoices for the day
        factory_invoices = Invoice.objects.filter(
            order__branch=branch,
            invoice_type='factory',
            invoice_date__range=(day_start, day_end),
            is_deleted=False
        ).select_related('order', 'order__customer')
        
        for invoice in factory_invoices:
            # Get payments for this order
            payments = OrderPayment.objects.filter(
                order=invoice.order,
                payment_date__range=(day_start, day_end),
                is_deleted=False,
                transaction_status='success'
            )
            
            for payment in payments:
                transaction_type = "save" if not payment.is_edited else "update"
                if payment.order.is_refund:
                    transaction_type = "refund"
                
                transactions.append({
                    "date": payment.payment_date.strftime('%Y-%m-%d'),
                    "time": payment.payment_date.strftime('%H:%M:%S'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "N/A",
                    "from_name": "factory_order",
                    "remark": payment.order.order_remark or "",
                    "type": transaction_type,
                    "special": "repayment" if payment.is_partial else "",
                    "amount": float(payment.amount),
                    "invoice_number": invoice.invoice_number,
                    "customer_name": invoice.order.customer.name
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_normal_orders(self, branch, day_start, day_end):
        """Get normal orders (invoice_type='normal')"""
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
                transaction_type = "save" if not payment.is_edited else "update"
                if payment.order.is_refund:
                    transaction_type = "refund"
                
                transactions.append({
                    "date": payment.payment_date.strftime('%Y-%m-%d'),
                    "time": payment.payment_date.strftime('%H:%M:%S'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "N/A",
                    "from_name": "normal_order",
                    "remark": payment.order.order_remark or "",
                    "type": transaction_type,
                    "special": "repayment" if payment.is_partial else "",
                    "amount": float(payment.amount),
                    "invoice_number": invoice.invoice_number,
                    "customer_name": invoice.order.customer.name
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_frame_only_orders(self, branch, day_start, day_end):
        """Get frame only orders"""
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
                transaction_type = "save" if not payment.is_edited else "update"
                if payment.order.is_refund:
                    transaction_type = "refund"
                
                transactions.append({
                    "date": payment.payment_date.strftime('%Y-%m-%d'),
                    "time": payment.payment_date.strftime('%H:%M:%S'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "N/A",
                    "from_name": "frame_only_order",
                    "remark": payment.order.order_remark or "",
                    "type": transaction_type,
                    "special": "repayment" if payment.is_partial else "",
                    "amount": float(payment.amount),
                    "order_id": order.id,
                    "customer_name": order.customer.name
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_hearing_orders(self, branch, day_start, day_end):
        """Get hearing orders (invoice_type='hearing')"""
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
                transaction_type = "save" if not payment.is_edited else "update"
                if payment.order.is_refund:
                    transaction_type = "refund"
                
                transactions.append({
                    "date": payment.payment_date.strftime('%Y-%m-%d'),
                    "time": payment.payment_date.strftime('%H:%M:%S'),
                    "user_name": payment.user.username if payment.user else payment.admin.username if payment.admin else "N/A",
                    "from_name": "hearing_order",
                    "remark": payment.order.order_remark or "",
                    "type": transaction_type,
                    "special": "repayment" if payment.is_partial else "",
                    "amount": float(payment.amount),
                    "invoice_number": invoice.invoice_number,
                    "customer_name": invoice.order.customer.name
                })
                total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_channel_payments(self, branch, day_start, day_end):
        """Get channel payments (appointments)"""
        transactions = []
        total = 0
        
        channel_payments = ChannelPayment.objects.filter(
            appointment__branch=branch,
            payment_date__range=(day_start, day_end),
            is_deleted=False
        ).select_related('appointment', 'appointment__patient', 'appointment__doctor')
        
        for payment in channel_payments:
            transaction_type = "save" if not payment.is_edited else "update"
            if payment.appointment.is_refund:
                transaction_type = "refund"
            
            transactions.append({
                "date": payment.payment_date.strftime('%Y-%m-%d'),
                "time": payment.payment_date.strftime('%H:%M:%S'),
                "user_name": "N/A",  # Channel payments don't have user tracking
                "from_name": "channel",
                "remark": payment.appointment.note or "",
                "type": transaction_type,
                "special": "repayment" if not payment.is_final else "",
                "amount": float(payment.amount),
                "appointment_id": payment.appointment.id,
                "patient_name": payment.appointment.patient.name,
                "doctor_name": payment.appointment.doctor.name
            })
            total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_soldering_orders(self, branch, day_start, day_end):
        """Get soldering order payments"""
        transactions = []
        total = 0
        
        soldering_payments = SolderingPayment.objects.filter(
            order__branch=branch,
            payment_date__range=(day_start, day_end),
            is_deleted=False,
            transaction_status='completed'
        ).select_related('order', 'order__patient')
        
        for payment in soldering_payments:
            transaction_type = "save"
            if payment.transaction_status == 'refunded':
                transaction_type = "refund"
            
            transactions.append({
                "date": payment.payment_date.strftime('%Y-%m-%d'),
                "time": payment.payment_date.strftime('%H:%M:%S'),
                "user_name": "N/A",  # Soldering payments don't have user tracking
                "from_name": "soldering_order",
                "remark": payment.order.note or "",
                "type": transaction_type,
                "special": "repayment" if payment.is_partial else "",
                "amount": float(payment.amount),
                "order_id": payment.order.id,
                "patient_name": payment.order.patient.name
            })
            total += float(payment.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_expenses(self, branch, target_date, source_type):
        """Get expenses by source type (safe/cash)"""
        transactions = []
        total = 0
        
        expenses = Expense.objects.filter(
            branch=branch,
            created_at__date=target_date,
            paid_source=source_type
        ).select_related('main_category', 'sub_category')
        
        for expense in expenses:
            source_name = "safe_expense" if source_type == 'safe' else "cashier_expense"
            
            transactions.append({
                "date": expense.created_at.strftime('%Y-%m-%d'),
                "time": expense.created_at.strftime('%H:%M:%S'),
                "user_name": "N/A",  # Expenses don't have user tracking in current model
                "from_name": source_name,
                "remark": expense.note or "",
                "type": "expense",
                "special": "refund" if expense.is_refund else "",
                "amount": float(expense.amount),
                "category": f"{expense.main_category.name} > {expense.sub_category.name}"
            })
            total += float(expense.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_banking_transactions(self, branch, target_date):
        """Get banking transactions (deposits)"""
        transactions = []
        total = 0
        
        deposits = BankDeposit.objects.filter(
            branch=branch,
            date=target_date
        ).select_related('bank_account')
        
        for deposit in deposits:
            transactions.append({
                "date": deposit.date.strftime('%Y-%m-%d'),
                "time": "N/A",  # BankDeposit doesn't have time
                "user_name": "N/A",  # BankDeposit doesn't have user tracking
                "from_name": "banking",
                "remark": deposit.note or "",
                "type": "deposit",
                "special": "confirmed" if deposit.is_confirmed else "pending",
                "amount": float(deposit.amount),
                "bank_account": f"{deposit.bank_account.bank_name} - {deposit.bank_account.account_number}"
            })
            total += float(deposit.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_safe_transactions(self, branch, target_date):
        """Get safe transactions"""
        transactions = []
        total = 0
        
        safe_transactions = SafeTransaction.objects.filter(
            branch=branch,
            date=target_date
        )
        
        for transaction in safe_transactions:
            amount = float(transaction.amount)
            if transaction.transaction_type == 'expense':
                amount = -amount  # Expenses are negative
            
            transactions.append({
                "date": transaction.date.strftime('%Y-%m-%d'),
                "time": transaction.created_at.strftime('%H:%M:%S'),
                "user_name": "N/A",  # SafeTransaction doesn't have user tracking
                "from_name": "safe",
                "remark": transaction.reason or "",
                "type": transaction.transaction_type,
                "special": "",
                "amount": amount,
                "reference_id": transaction.reference_id or ""
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
    
    def _get_other_income(self, branch, target_date):
        """Get other income transactions"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%Y-%m-%d'),
                "time": income.date.strftime('%H:%M:%S'),
                "user_name": "N/A",  # OtherIncome doesn't have user tracking
                "from_name": "other_income",
                "remark": income.note or "",
                "type": "income",
                "special": "",
                "amount": float(income.amount),
                "category": income.category.name
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
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
                "type": "save",
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
            source_name = "safe" if source_type == 'safe' else "cashier"
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
            special_indicator = "confirmed" if deposit.is_confirmed else "pending"
            
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
            special_indicator = "○"
            
            transactions.append({
                "date": transaction.date.strftime('%d/%m/%Y'),
                "time": transaction.created_at.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Safe",
                "remark": transaction.reason or "-",
                "type": transaction.transaction_type.title(),
                "special": special_indicator,
                "amount": f"Rs. {int(abs(amount))}"
            })
            total += amount
        
        return {"transactions": transactions, "total": total}
    
    def _get_other_income_flat(self, branch, target_date):
        """Get other income in flat table format"""
        transactions = []
        total = 0
        
        other_incomes = OtherIncome.objects.filter(
            branch=branch,
            date__date=target_date
        ).select_related('category')
        
        for income in other_incomes:
            transactions.append({
                "date": income.date.strftime('%d/%m/%Y'),
                "time": income.date.strftime('%I.%M%p'),
                "user_name": "-",
                "form_name": "Other Income",
                "remark": income.note or "-",
                "type": "Income",
                "special": "○",
                "amount": f"Rs. {int(income.amount)}"
            })
            total += float(income.amount)
        
        return {"transactions": transactions, "total": total}
    
    def _get_special_indicator(self, is_edited, is_partial, is_refund):
        """Get special indicator based on transaction status"""
        if is_refund:
            return "●"  # Filled circle for refunds
        elif is_edited or is_partial:
            return "●"  # Filled circle for edited/partial payments
        else:
            return "○"  # Empty circle for normal transactions
