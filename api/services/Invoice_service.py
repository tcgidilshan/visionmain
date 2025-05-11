from datetime import date
from django.db.models import Max
from ..models import Invoice, RefractionDetails
from rest_framework.exceptions import NotFound
from ..serializers import InvoiceSerializer,RefractionDetailsSerializer

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
    
    @staticmethod
    def get_invoice_by_order_id(order_id):
        """
        Retrieve an invoice by order_id and include refraction_details manually.
        """
        try:
            # ✅ Fetch the invoice, order, and refraction
            invoice = (
                Invoice.objects
                .select_related('order__refraction')  # ✅ Load related refraction
                .get(order_id=order_id)
            )

            # ✅ Manually fetch refraction_details using refraction_id
            refraction_details = RefractionDetails.objects.filter(refraction=invoice.order.refraction).first()

            # ✅ Serialize the invoice
            invoice_data = InvoiceSerializer(invoice).data  

            # ✅ Serialize refraction_details manually if it exists
            invoice_data["refraction_details"] = RefractionDetailsSerializer(refraction_details).data if refraction_details else None  

            return invoice_data

        except Invoice.DoesNotExist:
            raise NotFound("No invoice found for this order.")

    @staticmethod
    def get_invoice_by_id(invoice_id):
        """
        Retrieve an invoice by invoice_id.
        If no invoice is found, raises a NotFound exception.
        """
        try:
            return Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise NotFound("Invoice not found.")
        
    @staticmethod
    def search_factory_invoices(user, invoice_number=None, mobile=None, nic=None, branch_id=None):
        qs = Invoice.objects.filter(invoice_type='factory')

        # Handle invoice_number filtering by user branch
        if branch_id:
            qs = qs.filter(order__branch_id=branch_id)
        if invoice_number:
            user_branches = user.user_branches.all().values_list('branch_id', flat=True)
            if not user_branches:
                raise ValueError("User has no branches assigned.")

            qs = qs.filter(invoice_number=invoice_number, order__branch_id__in=user_branches)

        if mobile:
            qs = qs.filter(order__customer__phone_number=mobile)

        if nic:
            qs = qs.filter(order__customer__nic=nic)
        #branch what user curently using branch_id as param
        

        return qs.select_related('order', 'order__customer').order_by('-invoice_date')
    
    @staticmethod
    def get_invoice_by_invoice_number(invoice_type, invoice_number, is_frame_only=None):
        try:
            filters = {
                "invoice_type__iexact": invoice_type,
                "invoice_number": invoice_number
            }

            if is_frame_only is not None:
                filters["order__is_frame_only"] = int(is_frame_only)

            invoice = Invoice.objects.select_related(
                "order__customer", "order__refraction"
            ).get(**filters)

            return InvoiceSerializer(invoice).data

        except Invoice.DoesNotExist:
            raise NotFound("Invoice not found with the given type and number.")




