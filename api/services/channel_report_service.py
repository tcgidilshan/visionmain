from datetime import datetime
from django.db.models import Sum, Q, F
from api.models import Appointment, ChannelPayment
from ..services.time_zone_convert_service import TimezoneConverterService

class ChannelReportService:

    @staticmethod
    def get_channel_payments_by_date_and_branch(payment_date, branch_id):
        """
        Fetch and summarize all channel payments on a specific date and branch.
        """

        # Step 1: Filter ChannelPayments with timezone handling
        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(payment_date,None)
            payments = ChannelPayment.objects.filter(
                payment_date__range=(start_datetime, end_datetime),
                appointment__branch_id=branch_id
            ).select_related('appointment')
        except (ValueError, TypeError) as e:
            raise ValueError("Invalid payment date format. Use YYYY-MM-DD.")

        # Step 2: Group by appointment
        results = {}
        for payment in payments:
            appt_id = payment.appointment_id
            if appt_id not in results:
                results[appt_id] = {
                    "channel_id": appt_id,
                    "channel_no": payment.appointment.channel_no,
                    "invoice_number": payment.appointment.invoice_number,
                    "amount_cash": 0,
                    "amount_credit_card": 0,
                    "amount_online": 0,
                    "total_paid": 0,
                    "total_due": float(payment.appointment.amount),  # channeling_fee
                    "balance": 0,
                    'appointment_id': payment.appointment_id
                }

            method = payment.payment_method
            if method == 'cash':
                results[appt_id]["amount_cash"] += float(payment.amount)
            elif method == 'credit_card':
                results[appt_id]["amount_credit_card"] += float(payment.amount)
            elif method == 'online_transfer':
                results[appt_id]["amount_online"] += float(payment.amount)

            results[appt_id]["total_paid"] += float(payment.amount)
            results[appt_id]["balance"] = results[appt_id]["total_due"] - results[appt_id]["total_paid"]

        return list(results.values())
