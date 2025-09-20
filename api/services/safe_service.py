from django.db import transaction
from decimal import Decimal
from ..models import SafeTransaction, SafeBalance
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

class SafeService:
    @staticmethod
    @transaction.atomic
    def record_transaction(branch, expense, amount, transaction_type, reason="", reference_id=None):
        """
        Records or updates a transaction to the safe and updates the branch's safe balance.
        """
        # 💡 Always convert amount to Decimal safely
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        elif isinstance(amount, str):
            amount = Decimal(amount)

        # Check if a SafeTransaction already exists for this expense
        existing_transaction = SafeTransaction.objects.filter(
            expense=expense,
            branch=branch
        ).first()

        if existing_transaction:
            # Update the existing transaction
            old_amount = existing_transaction.amount
            existing_transaction.amount = amount
            existing_transaction.transaction_type = transaction_type
            existing_transaction.reason = reason
            existing_transaction.reference_id = reference_id
            existing_transaction.save()

            # Adjust balance by the difference
            balance_adjustment = amount - old_amount
        else:
            # Create new transaction
            SafeTransaction.objects.create(
                expense=expense,
                branch=branch,
                transaction_type=transaction_type,
                amount=amount,
                reason=reason,
                reference_id=reference_id
            )
            balance_adjustment = amount

        # Step 2: Get or create balance
        safe_balance, _ = SafeBalance.objects.get_or_create(branch=branch)

        # Ensure balance is Decimal (safety net)
        if isinstance(safe_balance.balance, float):
            safe_balance.balance = Decimal(str(safe_balance.balance))

        # Step 3: Update balance
        if transaction_type == SafeTransaction.TransactionType.INCOME:
            safe_balance.balance += balance_adjustment
        else:
            safe_balance.balance -= balance_adjustment

        safe_balance.save()
        return safe_balance
    
    @staticmethod
    def record_transaction_bank_deposit(branch, bank_deposit, amount, transaction_type, reason="", reference_id=None):
        """
        Records or updates a transaction to the safe and updates the branch's safe balance.
        """
        # 💡 Always convert amount to Decimal safely
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        elif isinstance(amount, str):
            amount = Decimal(amount)

        # Check if a SafeTransaction already exists for this bank deposit
        existing_transaction = SafeTransaction.objects.filter(
            bank_deposit=bank_deposit,
            branch=branch
        ).first()

        if existing_transaction:
            # Update the existing transaction
            old_amount = existing_transaction.amount
            existing_transaction.amount = amount
            existing_transaction.transaction_type = transaction_type
            existing_transaction.reason = reason
            existing_transaction.reference_id = reference_id
            existing_transaction.save()

            # Adjust balance by the difference
            balance_adjustment = amount - old_amount
        else:
            # Create new transaction
            SafeTransaction.objects.create(
                bank_deposit=bank_deposit,
                branch=branch,
                transaction_type=transaction_type,
                amount=amount,
                reason=reason,
                reference_id=reference_id
            )
            balance_adjustment = amount

        # Step 2: Get or create balance
        safe_balance, _ = SafeBalance.objects.get_or_create(branch=branch)

        # Ensure balance is Decimal (safety net)
        if isinstance(safe_balance.balance, float):
            safe_balance.balance = Decimal(str(safe_balance.balance))

        # Step 3: Update balance
        if transaction_type == SafeTransaction.TransactionType.INCOME:
            safe_balance.balance += balance_adjustment
        else:
            safe_balance.balance -= balance_adjustment

        safe_balance.save()
        return safe_balance
    @staticmethod
    def validate_sufficient_balance(branch_id, amount):
        try:
            safe_balance = SafeBalance.objects.get(branch_id=branch_id)
        except SafeBalance.DoesNotExist:
            raise ValidationError("Safe balance not found for this branch.")

        if safe_balance.balance < Decimal(amount):
            raise ValidationError("🚫 Insufficient funds in the Safe Locker for this expense.")
        
    @staticmethod
    def get_total_income(branch_id=None, from_date=None, to_date=None):
        queryset = SafeTransaction.objects.filter(transaction_type='income')

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)

        return queryset.aggregate(total=Sum("amount"))["total"] or 0
    
    @staticmethod
    def get_total_safe(branch_id=None):
        if branch_id:
            try:
                balance = SafeBalance.objects.get(branch_id=branch_id).balance
                return balance or Decimal('0.00')
            except SafeBalance.DoesNotExist:
                return Decimal('0.00')
        else:
            return SafeBalance.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

