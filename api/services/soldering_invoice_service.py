from django.utils.text import slugify
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import SolderingInvoice

class SolderingInvoiceService:
    @staticmethod
    @transaction.atomic
    def create_invoice(order):
        # 1. Check if invoice already exists
        if SolderingInvoice.objects.filter(order=order, is_deleted=False).exists():
            raise ValidationError("Invoice already exists for this order.")

        # 2. Prepare invoice number components
        branch_name = order.branch.branch_name.strip().upper()
        branch_code = slugify(branch_name)[:3].upper()  # 'Colombo' -> 'COL'

        existing_count = SolderingInvoice.objects.filter(
            order__branch=order.branch
        ).count()

        next_number = existing_count + 1
        padded_number = str(next_number).zfill(4)  # 0001, 0002, ...

        invoice_number = f"{branch_code}-SLD-{padded_number}"

        # 3. Create invoice
        invoice = SolderingInvoice.objects.create(
            invoice_number=invoice_number,
            invoice_date=timezone.now().date(),
            order=order
        )

        return invoice
