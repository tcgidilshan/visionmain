from django.db import models
from django.utils import timezone
from datetime import datetime, date
from typing import Dict, List, Optional, Union
from decimal import Decimal
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q, Sum, Count
from ..models import BankDeposit, BankAccount, Branch


class BankingService:
    """
    Service class for handling banking report operations
    """
    
    @staticmethod
    def get_banking_report(
        branch_id: int,
        start_date: Union[str, date],
        end_date: Union[str, date],
        is_confirmed: Optional[bool] = None
    ) -> Dict:
        """
        Get banking report for a specific branch within date range
        
        Args:
            branch_id (int): Branch ID to filter deposits
            start_date (str|date): Start date for filtering (YYYY-MM-DD format if string)
            end_date (str|date): End date for filtering (YYYY-MM-DD format if string)
            is_confirmed (bool, optional): Filter by confirmation status
            
        Returns:
            Dict: Banking report data with deposits and summary
            
        Raises:
            ValidationError: If parameters are invalid
            ObjectDoesNotExist: If branch doesn't exist
        """
        
        # Validate branch exists
        try:
            branch = Branch.objects.get(id=branch_id)
        except Branch.DoesNotExist:
            raise ObjectDoesNotExist(f"Branch with ID {branch_id} does not exist")
        
        # Convert string dates to date objects if needed
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError("start_date must be in YYYY-MM-DD format")
                
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError("end_date must be in YYYY-MM-DD format")
        
        # Validate date range
        if start_date > end_date:
            raise ValidationError("start_date cannot be greater than end_date")
        
        # Build query filters
        filters = Q(
            branch_id=branch_id,
            date__gte=start_date,
            date__lte=end_date
        )
        
        # Add confirmation filter if specified
        if is_confirmed is not None:
            filters &= Q(is_confirmed=is_confirmed)
        
        # Fetch deposits with related bank account data
        deposits = BankDeposit.objects.select_related(
            'bank_account', 
            'branch'
        ).filter(filters).order_by('-date', '-id')
        
        # Prepare deposit data
        deposit_list = []
        for deposit in deposits:
            deposit_data = {
                'id': deposit.id,
                'bank_name': deposit.bank_account.bank_name,
                'account_number': deposit.bank_account.account_number,
                'date': deposit.date.strftime('%Y-%m-%d'),
                'amount': float(deposit.amount),
                'is_confirmed': deposit.is_confirmed,
                'note': deposit.note or '',
            }
            deposit_list.append(deposit_data)
        
        # Calculate summary statistics
        summary_stats = BankingService._calculate_summary_stats(deposits)
        
        return {
            'branch': {
                'id': branch.id,
                'name': branch.branch_name,
                'location': branch.location
            },
            'filters': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'is_confirmed': is_confirmed
            },
            'deposits': deposit_list,
            'summary': summary_stats,
            'total_records': len(deposit_list)
        }
    
    @staticmethod
    def _calculate_summary_stats(deposits) -> Dict:
        """
        Calculate summary statistics for deposits
        
        Args:
            deposits: QuerySet of BankDeposit objects
            
        Returns:
            Dict: Summary statistics
        """
        
        # Use aggregation for efficient calculation
        stats = deposits.aggregate(
            total_amount=Sum('amount'),
            total_deposits=Count('id'),
            confirmed_deposits=Count('id', filter=Q(is_confirmed=True)),
            confirmed_amount=Sum('amount', filter=Q(is_confirmed=True)),
            pending_deposits=Count('id', filter=Q(is_confirmed=False)),
            pending_amount=Sum('amount', filter=Q(is_confirmed=False))
        )
        
        return {
            'total_amount': float(stats['total_amount'] or 0),
            'total_deposits': stats['total_deposits'] or 0,
            'confirmed_deposits': stats['confirmed_deposits'] or 0,
            'confirmed_amount': float(stats['confirmed_amount'] or 0),
            'pending_deposits': stats['pending_deposits'] or 0,
            'pending_amount': float(stats['pending_amount'] or 0),
            'confirmation_percentage': round(
                (stats['confirmed_deposits'] / max(stats['total_deposits'], 1)) * 100, 2
            )
        }
    
    @staticmethod
    def confirm_deposit(deposit_id: int, confirm_status: bool = True) -> Dict:
        """
        Confirm or unconfirm a bank deposit
        
        Args:
            deposit_id (int): ID of the deposit to update
            confirm_status (bool): True to confirm, False to unconfirm
            
        Returns:
            Dict: Updated deposit information
            
        Raises:
            ObjectDoesNotExist: If deposit doesn't exist
        """
        
        try:
            deposit = BankDeposit.objects.select_related(
                'bank_account', 
                'branch'
            ).get(id=deposit_id)
        except BankDeposit.DoesNotExist:
            raise ObjectDoesNotExist(f"Bank deposit with ID {deposit_id} does not exist")
        
        # Update confirmation status
        old_status = deposit.is_confirmed
        deposit.is_confirmed = confirm_status
        deposit.save(update_fields=['is_confirmed'])
        
        return {
            'id': deposit.id,
            'bank_name': deposit.bank_account.bank_name,
            'account_number': deposit.bank_account.account_number,
            'date': deposit.date.strftime('%Y-%m-%d'),
            'amount': float(deposit.amount),
            'is_confirmed': deposit.is_confirmed,
            'note': deposit.note or '',
            'status_changed': old_status != confirm_status,
            'branch': {
                'id': deposit.branch.id,
                'name': deposit.branch.branch_name
            }
        }