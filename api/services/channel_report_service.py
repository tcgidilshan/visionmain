from datetime import datetime
from django.db.models import Sum, Q, F
from api.models import Appointment, ChannelPayment, PaymentMethodBanks
from ..services.time_zone_convert_service import TimezoneConverterService

class ChannelReportService:

    @staticmethod
    def get_channel_payments_by_date_and_branch(payment_date, branch_id):
        """
        Fetch and summarize all channel payments on a specific date and branch.
        Includes soft-deleted, refunded appointments, and appointments with 0 payments.
        """

        # Step 1: Get appointments created on this date or deleted/refunded on this date
        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(payment_date, None)
            
            # Get all appointments that match the date criteria
            appointments = Appointment.all_objects.filter(
                Q(created_at__range=(start_datetime, end_datetime)) | 
                Q(deleted_at__range=(start_datetime, end_datetime)) |
                Q(refunded_at__range=(start_datetime, end_datetime)),
                branch_id=branch_id
            )
            
            # Get all payments for these appointments or payments made on this date
            payments = ChannelPayment.all_objects.filter(
                Q(payment_date__range=(start_datetime, end_datetime)) | 
                Q(appointment__in=appointments),
                appointment__branch_id=branch_id
            ).select_related('appointment', 'payment_method_bank')
            
        except (ValueError, TypeError) as e:
            raise ValueError("Invalid payment date format. Use YYYY-MM-DD.")

        # Get all active payment method banks for this branch (credit card banks only)
        branch_banks = PaymentMethodBanks.objects.filter(
            branch_id=branch_id,
            payment_method='credit_card',
            is_active=True
        ).values_list('name', flat=True)

        # Step 2: Initialize results with all appointments
        results = {}
        
        # First, add all appointments from the date range
        for appointment in appointments:
            appt_id = appointment.id
            results[appt_id] = {
                "channel_id": appt_id,
                "channel_no": appointment.channel_no,
                "invoice_number": appointment.invoice_number,
                "amount_cash": 0,
                "amount_credit_card": 0,
                "amount_online": 0,
                "total_paid": 0,
                "total_due": float(appointment.amount),  # channeling_fee
                "balance": float(appointment.amount),
                'appointment_id': appointment.id,
                'is_deleted': appointment.is_deleted,
                'is_refund': appointment.is_refund,
                'created_at': appointment.created_at.isoformat() if appointment.created_at else None,
                'deleted_at': appointment.deleted_at.isoformat() if appointment.deleted_at else None,
                'refunded_at': appointment.refunded_at.isoformat() if appointment.refunded_at else None,
            }
            # Initialize all branch banks with 0
            for bank_name in branch_banks:
                results[appt_id][bank_name] = 0
        
        # Step 3: Add payment data
        for payment in payments:
            appt_id = payment.appointment_id
            
            # If appointment is not in results, add it (for payments made on this date)
            if appt_id not in results:
                results[appt_id] = {
                    "channel_id": appt_id,
                    "channel_no": payment.appointment.channel_no,
                    "invoice_number": payment.appointment.invoice_number,
                    "amount_cash": 0,
                    "amount_credit_card": 0,
                    "amount_online": 0,
                    "total_paid": 0,
                    "total_due": float(payment.appointment.amount),
                    "balance": 0,
                    'appointment_id': payment.appointment_id,
                    'is_deleted': payment.appointment.is_deleted,
                    'is_refund': payment.appointment.is_refund,
                    'created_at': payment.appointment.created_at.isoformat() if payment.appointment.created_at else None,
                    'deleted_at': payment.appointment.deleted_at.isoformat() if payment.appointment.deleted_at else None,
                    'refunded_at': payment.appointment.refunded_at.isoformat() if payment.appointment.refunded_at else None,
                }
                # Initialize all branch banks with 0
                for bank_name in branch_banks:
                    results[appt_id][bank_name] = 0

            method = payment.payment_method
            if method == 'cash':
                results[appt_id]["amount_cash"] += float(payment.amount)
            elif method == 'credit_card':
                results[appt_id]["amount_credit_card"] += float(payment.amount)
            elif method == 'online_transfer':
                results[appt_id]["amount_online"] += float(payment.amount)

            results[appt_id]["total_paid"] += float(payment.amount)
            results[appt_id]["balance"] = results[appt_id]["total_due"] - results[appt_id]["total_paid"]
            
            # Add bank total if payment has a bank
            if payment.payment_method_bank:
                bank_name = payment.payment_method_bank.name
                if bank_name in results[appt_id]:
                    results[appt_id][bank_name] += float(payment.amount)

        return list(results.values())
