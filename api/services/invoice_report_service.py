from datetime import datetime
from django.db.models import Sum, Q
from api.models import Invoice, OrderPayment


class InvoiceReportService:

    @staticmethod
    def get_invoice_report_by_payment_date(payment_date_str, branch_id):
        """
        Returns filtered invoice data (factory & normal) based on payment date and branch.
        """

        try:
            payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid payment date format. Use YYYY-MM-DD.")

        # Get all payments made on that date for that branch
        payments = OrderPayment.objects.select_related("order").filter(
            payment_date__date=payment_date,
            order__branch_id=branch_id
        )

        # Organize payments by order
        payments_by_order = {}
        for payment in payments:
            oid = payment.order_id
            if oid not in payments_by_order:
                payments_by_order[oid] = {
                    "cash": 0,
                    "credit_card": 0,
                    "online_transfer": 0,
                    "total": 0
                }

            payments_by_order[oid][payment.payment_method] += float(payment.amount)
            payments_by_order[oid]["total"] += float(payment.amount)

        # Get all invoices where related order has at least 1 payment on that date
        invoice_qs = Invoice.objects.select_related("order").filter(
            order_id__in=payments_by_order.keys(),
            order__branch_id=branch_id,
            is_deleted=False,
            order__is_deleted=False
        )

        results = []

        for invoice in invoice_qs:
            order_id = invoice.order_id
            payment_data = payments_by_order.get(order_id, {})

            data = {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_type": invoice.invoice_type,
                "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d"),
                "order_id": order_id,
                "total_invoice_price": float(invoice.order.total_price),
                "total_cash_payment": payment_data.get("cash", 0),
                "total_credit_card_payment": payment_data.get("credit_card", 0),
                "total_online_payment": payment_data.get("online", 0),
                "total_payment": payment_data.get("total", 0),
                "balance": float(invoice.order.total_price) - payment_data.get("total", 0)
            }

            results.append(data)

        return results
