from datetime import date
from django.db.models import Max
from ..models import Invoice, RefractionDetails

class InvoiceService:
    """
    Service class to handle invoice creation based on new invoice type logic.
    """

    @staticmethod
    def create_invoice(order):
        """
        Generates an invoice for the given order.
        Assigns a daily invoice number for factory invoices.
        """

        # ✅ Step 1: Determine Invoice Type
        if RefractionDetails.objects.filter(refraction_id=order.refraction_id).exists():
            invoice_type = "factory"  # ✅ Factory if refraction details exist
        elif order.refraction_id:
            invoice_type = "manual"  # ✅ Manual if only refraction ID exists but no details
        else:
            invoice_type = "normal"  # ✅ Normal if no refraction at all

        # ✅ Step 2: Assign Daily Invoice No for Factory Invoices
        daily_invoice_no = None
        if invoice_type == "factory":
            today = date.today()
            last_invoice = Invoice.objects.filter(invoice_date=today).aggregate(Max("daily_invoice_no"))
            daily_invoice_no = (last_invoice["daily_invoice_no__max"] or 0) + 1  # Start from 1 if no invoice exists today

        # ✅ Step 3: Create Invoice Record
        invoice = Invoice.objects.create(
            order=order,
            invoice_date=date.today(),
            invoice_type=invoice_type,
            daily_invoice_no=daily_invoice_no,  # Only for factory invoices
        )
        return invoice
