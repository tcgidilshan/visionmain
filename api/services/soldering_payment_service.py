from ..models import SolderingPayment, SolderingOrder,PaymentMethodBanks
from ..serializers import SolderingPaymentSerializer
from rest_framework.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal


class SolderingPaymentService:
    @staticmethod
    def process_solder_payments(order, payments_data):

        total_paid = Decimal('0.00')
        payment_instances = []
        final_payment_flagged = False

        for payment in payments_data:
            amount = Decimal(str(payment.get('amount', 0)))

            # 1. Block all negative payments. Block zero unless order price is zero.
            if amount < 0 or (amount == 0 and order.price != 0):
                raise ValidationError("Zero-amount payment is only allowed if order price is zero.")

            method = payment.get('payment_method')
            is_final = payment.get('is_final_payment', False)
            bank_id = payment.get('payment_method_bank')
            payment_method_bank = None
            if bank_id:
                try:
                    payment_method_bank = PaymentMethodBanks.objects.get(id=bank_id)
                except PaymentMethodBanks.DoesNotExist:
                    raise ValidationError("Invalid payment_method_bank ID.")

            if is_final:
                if final_payment_flagged:
                    raise ValidationError("Only one payment can be marked as final.")
                final_payment_flagged = True

            total_paid += amount

            payment_instance = SolderingPayment.objects.create(
                order=order,
                amount=amount,
                payment_method=method,
                transaction_status=SolderingPayment.TransactionStatus.COMPLETED,
                is_final_payment=is_final,
                is_partial=False,
                payment_method_bank=payment_method_bank
            )

            payment_instances.append(payment_instance)

        if total_paid > order.price:
            raise ValidationError("Total payments exceed the order price.")

        # Determine partial flags
        is_full_payment = total_paid == order.price
        for payment in payment_instances:
            payment.is_partial = not is_full_payment
            payment.save()

        return payment_instances

    @staticmethod
    def add_repayment(order, amount, payment_method, is_final_payment=False, payment_method_bank=None):
        """
        Add a repayment for a soldering order with validation.
        This method now uses DRF's ValidationError to ensure API-friendly errors.
        """
        # Block repayments to deleted orders
        if order.is_deleted:
            raise ValidationError("Cannot add repayment to a deleted order.")

        # Sum existing payments (exclude soft-deleted)
        total_paid = SolderingPayment.objects.filter(
            order=order, is_deleted=False
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        remaining = order.price - total_paid

        # Block invalid or overpayment amounts
        if amount <= 0:
            raise ValidationError("Repayment amount must be positive.")
        if amount > remaining:
            raise ValidationError("Repayment exceeds remaining order balance.")

        # Allow only one final payment
        if is_final_payment and SolderingPayment.objects.filter(
            order=order, is_final_payment=True, is_deleted=False
        ).exists():
            raise ValidationError("A final payment has already been made for this order.")

        bank_instance = None
        if payment_method_bank:
            try:
                bank_instance = PaymentMethodBanks.objects.get(id=payment_method_bank)
            except PaymentMethodBanks.DoesNotExist:
                raise ValidationError("Invalid payment_method_bank ID.")

        # Create and return the payment instance
        payment = SolderingPayment.objects.create(
            order=order,
            amount=amount,
            payment_method=payment_method,
            transaction_status=SolderingPayment.TransactionStatus.COMPLETED,
            is_final_payment=is_final_payment,
            is_partial=(amount != remaining),
            payment_method_bank=bank_instance
        )
        return payment

    @staticmethod
    @transaction.atomic
    def append_on_change_payments_for_order(order, payments_data, admin_id, user_id):
        """
        Medical-compliant payment update with append-on-change logic for SolderingOrder.
        1. For each payment in input:
            - If id provided, check if data changed.
                - If changed: soft-delete old, create new (copying date).
                - If not changed: skip.
            - If no id: create new.
        2. Soft-delete any DB payments not referenced in input.
        """
        db_payments = {p.id: p for p in order.payments.filter(is_deleted=False)}
        seen_payment_ids = set()
        total_paid = 0
        payment_records = []

        for i, payment in enumerate(payments_data):
            payment_id = payment.get("id")
            amount = float(payment.get('amount', 0))
            method = payment.get('payment_method')
            txn_status = payment.get('transaction_status', SolderingPayment.TransactionStatus.COMPLETED)
            payment_method_bank = payment.get('payment_method_bank', None)

            if amount <= 0:
                raise ValidationError(f"Payment #{i+1}: Amount must be greater than 0.")
            if not method:
                raise ValidationError(f"Payment #{i+1}: payment_method is required.")

            if payment_id:
                old_payment = db_payments.get(payment_id)
                if old_payment:
                    seen_payment_ids.add(payment_id)
                    changed = (
                        float(old_payment.amount) != amount or
                        old_payment.payment_method != method or
                        old_payment.transaction_status != txn_status or 
                        (old_payment.payment_method_bank.id if old_payment.payment_method_bank else None) != payment_method_bank
                    )
                    if changed:
                        old_payment.is_deleted = True
                        old_payment.deleted_at = old_payment.payment_date
                        old_payment.save(update_fields=['is_deleted', 'deleted_at'])
                        payment_data = {
                            "order": order.id,
                            "amount": amount,
                            "payment_method": method,
                            "transaction_status": txn_status,
                            "payment_date": old_payment.payment_date,
                            "is_partial": False,
                            "is_final_payment": False,
                            "payment_method_bank": payment_method_bank,
                        }
                        payment_serializer = SolderingPaymentSerializer(data=payment_data)
                        payment_serializer.is_valid(raise_exception=True)
                        new_payment = payment_serializer.save()
                        payment_records.append(new_payment)
                        total_paid += amount
                    else:
                        payment_records.append(old_payment)
                        total_paid += float(old_payment.amount)
                else:
                    raise ValidationError(f"Payment id {payment_id} not found for this order.")
            else:
                payment_data = {
                    "order": order.id,
                    "amount": amount,
                    "payment_method": method,
                    "transaction_status": txn_status,
                    "is_partial": False,
                    "is_final_payment": False,
                    "payment_method_bank": payment_method_bank,
                }
                payment_serializer = SolderingPaymentSerializer(data=payment_data)
                payment_serializer.is_valid(raise_exception=True)
                new_payment = payment_serializer.save()
                payment_records.append(new_payment)
                total_paid += amount

        for db_id, db_pmt in db_payments.items():
            if db_id not in seen_payment_ids:
                db_pmt.is_deleted = True
                db_pmt.deleted_at = db_pmt.payment_date
                db_pmt.save(update_fields=['is_deleted', 'deleted_at'])

        running_total = 0
        for p in payment_records:
            running_total += float(p.amount)
            p.is_final_payment = (round(running_total, 2) == round(float(order.price), 2))
            p.is_partial = (running_total < float(order.price))
            p.save()

        if round(total_paid, 2) > round(float(order.price), 2):
            raise ValidationError("Total payments exceed the order price. No payments saved.")

        return total_paid

