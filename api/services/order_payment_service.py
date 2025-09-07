from ..models import OrderPayment,Order,Expense
from ..serializers import OrderPaymentSerializer
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from ..serializers import ExpenseSerializer
from django.db import transaction
#sum
from django.db.models import Sum
class OrderPaymentService:
    """
    Handles processing of order payments.
    """
    @staticmethod
    def process_payments(order, payments_data):
        if order.is_deleted:
            raise ValidationError("Cannot process payments for a deleted order.")
        total_payment = 0
        for payment_data in payments_data:
            payment_data['order'] = order.id

            # Determine if this payment is partial
            payment_data['is_partial'] = total_payment + payment_data['amount'] < order.total_price

            # Validate and save each payment
            order_payment_serializer = OrderPaymentSerializer(data=payment_data)
            order_payment_serializer.is_valid(raise_exception=True)
            payment_instance = order_payment_serializer.save()

            # Track total payment
            total_payment += payment_data['amount']

            # Check if this is the final payment
            payment_instance.is_final_payment = total_payment == order.total_price
            payment_instance.save()

        return total_payment
    
    @staticmethod
    def update_process_payments(order, payments_data,admin_id,user_id):
        """
        Updates existing payments, creates new ones if needed, and removes old ones.
        """
        existing_payments = {payment.id: payment for payment in order.orderpayment_set.all()}
        new_payment_ids = set()
        total_payment = 0

        for payment_data in payments_data:
            payment_id = payment_data.get("id")  # Check if payment exists

            if payment_id and payment_id in existing_payments:
                # Update existing payment
                existing_payment = existing_payments.pop(payment_id)
                existing_payment.amount = payment_data.get("amount", existing_payment.amount)
                existing_payment.payment_method = payment_data.get("payment_method", existing_payment.payment_method)
                existing_payment.transaction_status = payment_data.get("transaction_status", existing_payment.transaction_status)
                existing_payment.is_partial = total_payment + existing_payment.amount < order.total_price
                existing_payment.save()
                new_payment_ids.add(payment_id)
                total_payment += existing_payment.amount

            else:
                # Create a new payment
                payment_data['order'] = order.id
                payment_data['is_partial'] = total_payment + payment_data['amount'] < order.total_price

                order_payment_serializer = OrderPaymentSerializer(data=payment_data)
                order_payment_serializer.is_valid(raise_exception=True)
                payment_instance = order_payment_serializer.save()

                new_payment_ids.add(payment_instance.id)
                total_payment += payment_data['amount']

        # Remove payments that were not in the update request
        for old_payment in existing_payments.values():
            old_payment.delete()

        # Ensure total payments do not exceed the order total
        if total_payment > order.total_price:
            raise ValueError("Total payments exceed the order total price.")

        return total_payment
    
    @staticmethod
    def get_payments(order_id=None, invoice_id=None):
        """
        Fetch payments for a given order ID or invoice ID.
        """
        try:
            # Fetch order using order_id or invoice_id
            if order_id:
                order = Order.objects.get(id=order_id)
            elif invoice_id:
                order = Order.objects.get(invoice_id=invoice_id)
            else:
                return {"error": "Order ID or Invoice ID is required."}

            # Get payments related to the order
            payments = order.orderpayment_set.all()

            # Serialize payment data
            payment_serializer = OrderPaymentSerializer(payments, many=True)

            return {
                "message": "Payments fetched successfully.",
                "payments": payment_serializer.data
            }

        except Order.DoesNotExist:
            return {"error": "Order not found."}
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}
        
    @staticmethod
    def refund_order(order_id, expense_data):
        try:
            order = Order.all_objects.get(id=order_id)
        except Order.DoesNotExist:
            raise ValidationError("Order not found.")
    
        if order.is_refund:
            raise ValidationError("This order has already been refunded.")
        
    # Get total amount paid by customer
    #get all payments 
        payments = OrderPayment.all_objects.filter(is_deleted=False,is_edited=False,order=order_id)
       
        total_paid = (
            OrderPayment.all_objects
            .filter(is_deleted=False,is_edited=False,order=order_id)
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        
        if total_paid == 0:
            raise ValidationError("No successful payments found to refund.")
        now = timezone.now()
        for payment in payments:
            payment.is_deleted = True
            payment.deleted_at = now
            payment.save()
        # Mark order as refunded
        order.is_refund = True
        order.refunded_at = timezone.now()
        order.refund_note = f"Refund processed on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        order.save()

        # Get invoice number if exists
        try:
            invoice_number = order.invoice.invoice_number
            note = f"Refund Invoice {invoice_number}"
        except Invoice.DoesNotExist:
            note = f"Refund for No invoice Number"
            
        # Prepare expense data
        expense_data['amount'] = str(total_paid)
        expense_data['paid_source'] = 'cash'
        expense_data['paid_from_safe'] = False
        expense_data['note'] = note
        expense_data['is_refund'] = True

        # Create expense
        serializer = ExpenseSerializer(data=expense_data)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()

        return {
            "message": "Order refund processed successfully.",
            "order_id": order.id,
            "refund_expense_id": expense.id
        }
    @staticmethod
    @transaction.atomic
    def append_on_change_payments_for_order(order, payments_data,admin_id,user_id):
        """
        Medical-compliant payment update with append-on-change logic.
        1. For each payment in input:
            - If id provided, check if data changed.
                - If changed: soft-delete old, create new (copying date).
                - If not changed: skip.
            - If no id: create new.
        2. Soft-delete any DB payments not referenced in input.
        """
        # 1. Index all current, non-deleted payments by id for lookup
        db_payments = {p.id: p for p in order.orderpayment_set.filter(is_deleted=False)}
        seen_payment_ids = set()
        total_paid = 0
        payment_records = []

        for i, payment in enumerate(payments_data):
            payment_id = payment.get("id")
            amount = float(payment.get('amount', 0))
            method = payment.get('payment_method')
            txn_status = payment.get('transaction_status', 'success')
            payment_method_bank = payment.get('payment_method_bank', None)

            # --- Validation
            if amount <= 0:
                raise ValidationError(f"Payment #{i+1}: Amount must be greater than 0.")
            if not method:
                raise ValidationError(f"Payment #{i+1}: payment_method is required.")

            if payment_id:
                old_payment = db_payments.get(payment_id)
                if old_payment:
                    seen_payment_ids.add(payment_id)
                    # Compare each tracked field. You can expand this as needed.
                    changed = (
                        float(old_payment.amount) != amount or
                        old_payment.payment_method != method or
                        old_payment.transaction_status != txn_status or 
                        (old_payment.payment_method_bank.id if old_payment.payment_method_bank else None) != payment_method_bank
                    )
                    if changed:
                        # Soft-delete old, create new (keep date)
                        old_payment.user_id = user_id
                        old_payment.admin_id = admin_id
                        old_payment.is_edited = True
                        old_payment.save(update_fields=['user', 'admin'])
                        old_payment.delete()
                        payment_data = {
                            "order": order.id,
                            "amount": amount,
                            "payment_method": method,
                            "transaction_status": txn_status,
                            "payment_date": old_payment.payment_date,  # Carry forward
                            "is_partial": False,
                            "is_final_payment": False,
                            "payment_method_bank": payment_method_bank,
                            "user": None,
                            "admin": None,
                            
                        }
                        payment_serializer = OrderPaymentSerializer(data=payment_data)
                        payment_serializer.is_valid(raise_exception=True)
                        new_payment = payment_serializer.save()
                        payment_records.append(new_payment)
                        total_paid += amount
                    else:
                        # No change, keep the original (skip creating)
                        payment_records.append(old_payment)
                        total_paid += float(old_payment.amount)
                else:
                    # Edge case: id provided but not found (invalid/old)
                    raise ValidationError(f"Payment id {payment_id} not found for this order.")
            else:
                # No ID: Always create new payment (fresh entry)
                payment_data = {
                    "order": order.id,
                    "amount": amount,
                    "payment_method_bank": payment_method_bank,
                    "payment_method": method,
                    "transaction_status": txn_status,
                    "is_partial": False,
                    "is_final_payment": False,
                    "admin": None,
                    "user": None,
                }
                payment_serializer = OrderPaymentSerializer(data=payment_data)
                payment_serializer.is_valid(raise_exception=True)
                new_payment = payment_serializer.save()
                payment_records.append(new_payment)
                total_paid += amount

        # 2. Soft-delete payments that are in DB but not referenced in the new list (user "removed" them)
        for db_id, db_pmt in db_payments.items():
            if db_id not in seen_payment_ids:
                db_pmt.user_id = user_id
                db_pmt.admin_id = admin_id
                db_pmt.is_edited = True
                db_pmt.save(update_fields=['user', 'admin'])
                db_pmt.delete()

        # 3. Set is_partial and is_final_payment
        running_total = 0
        for p in payment_records:
            running_total += float(p.amount)
            p.is_final_payment = (round(running_total, 2) == round(float(order.total_price), 2))
            p.is_partial = (running_total < float(order.total_price))
            p.save()

        # 4. Overpayment check
        if round(total_paid, 2) > round(float(order.total_price), 2):
            raise ValidationError("Total payments exceed the order total price. No payments saved.")

        return total_paid