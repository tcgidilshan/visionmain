from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework.authtoken.models import Token as BaseToken
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from django.db.models import Max,Sum,Q
from .managers import SoftDeleteManager
from django.db import IntegrityError

class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class Branch(models.Model):
    branch_name = models.CharField(max_length=255)  # Name of the branch
    location = models.TextField()  # Branch location (address or details)
    created_at = models.DateTimeField(auto_now_add=True)  # Auto-created timestamp
    updated_at = models.DateTimeField(auto_now=True)  # Auto-updated timestamp

    def __str__(self):
        return self.branch_name
    
class BankAccount(models.Model):
    account_number = models.CharField(max_length=255, unique=True)
    bank_name = models.CharField(max_length=255)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)  # Linking bank account to branch
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"
    
class BankDeposit(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    is_confirmed = models.BooleanField(default=False)  # ✅ For "ticking" confirmed deposits
    note = models.TextField(blank=True, null=True)

class CustomUser(AbstractUser):
    mobile = models.CharField(max_length=15, blank=True, null=True)
    user_code = models.CharField(max_length=10, null=True, blank=True) 

    def __str__(self):
        return f"{self.username} ({self.user_code})"
    
#refractions
class Refraction(models.Model):
    unique_together = ('refraction_number', 'branch')
    patient = models.ForeignKey(
        'Patient', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="refractions"
    )
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.CASCADE,
        related_name='refractions',
        null=True,
        blank=True
    )
    customer_full_name = models.CharField(max_length=255)
    customer_mobile = models.CharField(max_length=15)
    refraction_number = models.CharField(max_length=10, blank=True)
    nic = models.CharField(max_length=12, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Generate refraction_number per branch if not set
        if not self.refraction_number and self.branch:
            last_refraction = Refraction.objects.filter(branch=self.branch).order_by('-id').first()
            
            if last_refraction and last_refraction.refraction_number.isdigit():
                last_number = int(last_refraction.refraction_number)
                self.refraction_number = str(last_number + 1).zfill(3)
            else:
                self.refraction_number = "001"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_full_name} - Refraction ID: {self.id} - {self.refraction_number} - Patient: {self.patient.name if self.patient else 'No Patient'}"

class Patient(models.Model):
    name = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    nic = models.CharField(max_length=15, null=True, blank=True)
    refraction = models.ForeignKey(
        Refraction, null=True, blank=True, on_delete=models.SET_NULL, related_name="patients"
    )
    patient_note = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name
    
class RefractionDetails(models.Model):
    refraction = models.OneToOneField(
        Refraction, on_delete=models.CASCADE, related_name="refraction_details",blank=True, null=True
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="refraction_details", blank=True, null=True
    )
    is_manual = models.BooleanField(default=False) 
    # Hb Rx
    hb_rx_right_dist = models.CharField(max_length=20, blank=True, null=True)  # Right Eye Hb Rx Dist
    hb_rx_left_dist = models.CharField(max_length=20, blank=True, null=True)   # Left Eye Hb Rx Dist
    hb_rx_right_near = models.CharField(max_length=20, blank=True, null=True)  # Right Eye Hb Rx Near
    hb_rx_left_near = models.CharField(max_length=20, blank=True, null=True)   # Left Eye Hb Rx Near

    # Auto Ref
    auto_ref_right = models.CharField(max_length=20, blank=True, null=True)  # Auto Ref Right
    auto_ref_left = models.CharField(max_length=20, blank=True, null=True)   # Auto Ref Left

    # NTC
    ntc_right = models.CharField(max_length=20, blank=True, null=True)  # NTC Right
    ntc_left = models.CharField(max_length=20, blank=True, null=True)   # NTC Left

    # VA Without Glass
    va_without_glass_right = models.CharField(max_length=20, blank=True, null=True)  # VA Without Glass Right
    va_without_glass_left = models.CharField(max_length=20, blank=True, null=True)   # VA Without Glass Left

    # VA Without P/H
    va_without_ph_right = models.CharField(max_length=20, blank=True, null=True)  # VA Without P/H Right
    va_without_ph_left = models.CharField(max_length=20, blank=True, null=True)   # VA Without P/H Left

    # VA With Glass
    va_with_glass_right = models.CharField(max_length=20, blank=True, null=True)  # VA With Glass Right
    va_with_glass_left = models.CharField(max_length=20, blank=True, null=True)   # VA With Glass Left

    # Right Eye Fields
    right_eye_dist_sph = models.CharField(max_length=10, blank=True, null=True)
    right_eye_dist_cyl = models.CharField(max_length=10, blank=True, null=True)
    right_eye_dist_axis = models.CharField(max_length=10, blank=True, null=True)
    right_eye_near_sph = models.CharField(max_length=10, blank=True, null=True)

    # Left Eye Fields
    left_eye_dist_sph = models.CharField(max_length=10, blank=True, null=True)
    left_eye_dist_cyl = models.CharField(max_length=10, blank=True, null=True)
    left_eye_dist_axis = models.CharField(max_length=10, blank=True, null=True)
    left_eye_near_sph = models.CharField(max_length=10, blank=True, null=True)
    note = models.CharField(max_length=100, blank=True, null=True)

    #new Changes
    cataract = models.BooleanField(default=False)
    blepharitis = models.BooleanField(default=False)
    refraction_remark = models.CharField(max_length=100, blank=True, null=True)
    shuger=models.BooleanField(default=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,  
        null=True,
        blank=True,
        related_name="refraction_details",
    )
    class PrescriptionType(models.TextChoices):
        INTERNAL = 'internal', 'Internal Prescription'
        VISION_PLUS = 'vision_plus', 'Vision Plus Prescription'
        OTHER = 'other', 'Other Prescription'

    # Replace this:
    # prescription = models.BooleanField(default=False)

    # With this:
    prescription_type = models.CharField(
        max_length=20,
        choices=PrescriptionType.choices,
        default=PrescriptionType.INTERNAL
    )
    
    def __str__(self):
        if self.is_manual:
            return f"Manual Refraction Details - ID {self.id}"
        
        if self.refraction:
            return f"Details for {self.refraction.customer_full_name}"
        
        return f"Details for Refraction {self.refraction.id if self.refraction else 'N/A'}"

#brands
class Brand(models.Model):
    BRAND_TYPES = [
        ('frame', 'Frame Brand'),
        ('lens', 'Lens Brand'),
        ('both', 'Both Frame & Lens')
    ]
    name = models.CharField(max_length=255, unique=True)
    brand_type = models.CharField(max_length=10, choices=BRAND_TYPES, default='both')
    def __str__(self):
        return f"{self.name} ({self.get_brand_type_display()})"
    
class ExternalLensBrand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return f"{self.name})"
   
#color    
class Color(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

#code
class Code(models.Model):
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, related_name='codes', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    
class Frame(models.Model):
    BRAND_CHOICES = (
        ('branded', 'Branded'),
        ('non_branded', 'Non-Branded'),
    )
    brand = models.ForeignKey(Brand, related_name='frames', on_delete=models.CASCADE)
    brand_type = models.CharField(max_length=20, choices=BRAND_CHOICES)
    code = models.ForeignKey(Code, related_name='frames', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, related_name='frames', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=50)
    species = models.CharField(max_length=100)
    image = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.brand.name} - {self.code.name} - {self.color.name} - {self.get_brand_type_display()}"
    class Meta:
        unique_together = (
            'brand',
            'brand_type',
            'code',
            'color',
            'species',
            'size',
        )
    verbose_name = "Frame"
    verbose_name_plural = "Frames"
    
class FrameStock(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="frame_stocks", null=True, blank=True)
    frame = models.ForeignKey(Frame, related_name='stocks', on_delete=models.CASCADE)
    qty = models.IntegerField(default=0)
    initial_count = models.IntegerField(null=True, blank=True)
    limit = models.IntegerField(default=0) 

    def __str__(self):
        return f"Frame: {self.frame.id} - Qty: {self.qty}"
    
class LenseType(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)  # Allows NULL and empty values

    def __str__(self):
        return self.name
    
class Coating(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)  # Allows NULL and empty values

    def __str__(self):
        return self.name
class ExternalLensCoating(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)  # Allows NULL and empty values

    def __str__(self):
        return self.name
    
class Lens(models.Model):
    type = models.ForeignKey(LenseType, related_name='lenses', on_delete=models.CASCADE)
    coating = models.ForeignKey(Coating, related_name='lenses', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name='lenses', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.type.name} - {self.coating.name} - ${self.price}"
    
class LensStock(models.Model):
    lens = models.ForeignKey(Lens, related_name='stocks', on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="stocks", null=True, blank=True)
    initial_count = models.IntegerField(null=True, blank=True)  # Allows NULL for optional initial count
    qty = models.IntegerField(default=0)
    limit = models.IntegerField(default=0)  # New column to define stock limit
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set on creation
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  
        return f"Lens: {self.lens.id} - Qty: {self.qty} - Limit: {self.limit}"
    
class Power(models.Model):
    name = models.CharField(max_length=255)
    

    def __str__(self):
        return f"{self.name}"
    
class LensPower(models.Model):
    SIDE_CHOICES = [
        ('left', 'Left'),
        ('right', 'Right'),
    ]
    lens = models.ForeignKey(Lens, related_name='lens_powers', on_delete=models.CASCADE)
    power = models.ForeignKey('Power', related_name='lens_powers', on_delete=models.CASCADE)  # Assuming Power table exists
    value = models.DecimalField(max_digits=5, decimal_places=2)
    side = models.CharField(
        max_length=10,
        choices=SIDE_CHOICES,
        null=True, 
        blank=True 
    )

    def __str__(self):
        return f"Lens: {self.lens.id} - Power: {self.value} ({self.side})" 
class LensCleaner(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)  # ✅ Soft delete flag

    def __str__(self):
        return self.name
    
class LensCleanerStock(models.Model):
    lens_cleaner = models.ForeignKey(LensCleaner, related_name='stocks', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.CASCADE,
        related_name='lens_cleaner_stocks',
        null=True,
        blank=True
    )
    initial_count = models.IntegerField(null=True, blank=True)  # Allows NULL for optional initial stock
    qty = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.lens_cleaner.name} - Qty: {self.qty} - Branch: {self.branch.branch_name if self.branch else 'N/A'}"
    
class Order(models.Model):
    progress_status = models.CharField(
        max_length=30,
        choices=[
            ('received_from_customer', 'Received from Customer'),
            ('issue_to_factory', 'Issued to Factory'),
            ('received_from_factory', 'Received from Factory'),
            ('issue_to_customer', 'Issued to Customer'),
        ],
        default='received_from_customer',
        null=True,
        blank=True
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(Patient, related_name='orders', on_delete=models.CASCADE)
    refraction = models.ForeignKey(Refraction, null=True, blank=True, on_delete=models.SET_NULL)
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.CASCADE,
        related_name='orders',
        null=True,
        blank=True 
    )
    order_date = models.DateTimeField(auto_now_add=True)
    order_updated_date = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    sales_staff_code = models.ForeignKey(CustomUser,related_name='orders',on_delete=models.CASCADE, null=True, blank=True)
    order_remark = models.TextField(null=True, blank=True)  # New field
    pd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    right_height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    left_height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    left_pd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    right_pd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    fitting_on_collection=models.BooleanField(default=False)
    on_hold=models.BooleanField(default=False)
    user_date = models.DateField(null=True, blank=True)
    is_frame_only = models.BooleanField(default=False) 
    bus_title = models.ForeignKey(
        'BusSystemSetting',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      # Only active records
    all_objects = models.Manager() 

    def __str__(self):
        return f"Order {self.id} - Status: {self.status} - Customer: {self.customer.id}"
    
    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
class ExternalLens(models.Model):
    BRAND_CHOICES = (
        ('branded', 'Branded'),
        ('non_branded', 'Non-Branded'),
    )

    branch     = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='external_lenses', null=True, blank=True)
    lens_type  = models.ForeignKey(LenseType, related_name='external_lenses', on_delete=models.CASCADE)
    coating    = models.ForeignKey(ExternalLensCoating, related_name='external_lenses', on_delete=models.CASCADE)
    brand      = models.ForeignKey(ExternalLensBrand, related_name='external_lenses', on_delete=models.CASCADE)
    branded    = models.CharField(max_length=20, choices=BRAND_CHOICES)
    price      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.brand.name} - {self.lens_type.name} ({self.coating.name}) – {self.get_branded_display()} – LKR {self.price or 'N/A'}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['lens_type', 'coating', 'brand', 'branded'],
                name='unique_external_lens_combination'
            )
        ]
        ordering = ['lens_type', 'coating']
        verbose_name = "External Lens"
        verbose_name_plural = "External Lenses"

class Invoice(models.Model):
    INVOICE_TYPES = [
        ('factory', 'Factory Invoice'),  # Linked to an order with refraction
        ('manual', 'Manual Invoice')  # Linked to an order without refraction
    ]

    lens_arrival_status = models.CharField(
        max_length=20,
        choices=[('received', 'Received'), ('not_received', 'Not Received')],
        null=True, blank=True
    )

    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_type = models.CharField(max_length=10, choices=INVOICE_TYPES)  #  Identifies invoice type
    daily_invoice_no = models.CharField(max_length=10,null=True, blank=True)  #  Factory invoices get a daily number
    invoice_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    invoice_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ['invoice_date', 'daily_invoice_no']  # Ensures daily numbering uniqueness
        constraints = [
            models.UniqueConstraint(fields=["invoice_number"], name="unique_invoice_number")
        ]
        
    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        # Always ensure invoice_date is set
        if not self.invoice_date:
            self.invoice_date = timezone.now()

        if not self.invoice_number:
            if not self.order or not self.order.branch:
                raise ValueError("Invoice must be linked to an order with a valid branch.")

            branch_code = self.order.branch.branch_name[:3].upper()
            invoice_day = self.invoice_date.strftime('%d')  # Get day as 2-digit string
            sequence_number = 1  # Default start

            with transaction.atomic():
                prefix = ""
                number = 1  # default starting number

                if self.invoice_type == 'factory':
                    prefix = f"{branch_code}{invoice_day}"

                    last_invoice = Invoice.objects.select_for_update().filter(
                        invoice_type='factory',
                        invoice_number__startswith=prefix
                    ).order_by('-id').first()

                elif self.invoice_type == 'normal':
                    prefix = f"{branch_code}N"
                    last_invoice = Invoice.objects.select_for_update().filter(
                        invoice_type='normal',
                        invoice_number__startswith=prefix
                    ).order_by('-id').first()

                if last_invoice and last_invoice.invoice_number:
                    try:
                        # Use replace only once, to avoid errors in edge cases
                        last_number = int(last_invoice.invoice_number.replace(prefix, '', 1))
                        number = last_number + 1
                    except ValueError:
                        number = 1  # fallback in case of bad data

                # Format invoice number
                if self.invoice_type == 'factory':
                    self.invoice_number = f"{prefix}{str(number).zfill(5)}"
                elif self.invoice_type == 'normal':
                    self.invoice_number = f"{prefix}{number}"

        super().save(*args, **kwargs)

class OtherItem(models.Model):
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ${self.price} - {'Active' if self.is_active else 'Inactive'}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    lens = models.ForeignKey(Lens, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    external_lens = models.ForeignKey(ExternalLens, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    lens_cleaner = models.ForeignKey(LensCleaner, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    other_item = models.ForeignKey(OtherItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    frame = models.ForeignKey(Frame, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    is_non_stock = models.BooleanField(default=False)  # ✅ Mark Non-Stock Items
    note = models.TextField(blank=True, null=True)
    whatsapp_sent = models.CharField(max_length=20,
    choices=[
        ('sent', 'Sent'),
        ('not_sent', 'Not Sent'),
    ],
    null=True,
    blank=True
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
       # Dynamically calculate subtotal on save
       self.subtotal = self.quantity * self.price_per_unit
       super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order.id} Item - Subtotal: {self.subtotal}"
    
    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
class OrderPayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
        ('online_transfer', 'Online Transfer'),
    ]

    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey(Order, related_name='orderpayment_set', on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    is_final_payment = models.BooleanField(default=False)
    is_partial = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment for Order {self.order.id} - Amount: {self.amount}"

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
class Doctor(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
    ]
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=100, blank=True, null=True) 
    contact_info = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    def __str__(self):
        return f"{self.name} ({self.specialization}) - {self.status}"

class Schedule(models.Model):
    class StatusChoices(models.TextChoices):
        AVAILABLE = 'Available', _('Available')
        BOOKED = 'Booked', _('Booked')
        UNAVAILABLE = 'Unavailable', _('Unavailable')

    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE, related_name='schedules')
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    start_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.AVAILABLE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('doctor', 'branch', 'date', 'start_time') 

    def __str__(self):
        return f"{self.doctor} - {self.date} ({self.start_time}) - {self.status}"

class Appointment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'Pending', _('Pending')
        CONFIRMED = 'Confirmed', _('Confirmed')
        COMPLETED = 'Completed', _('Completed')
        CANCELLED = 'Cancelled', _('Cancelled')

    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE, related_name='appointments')
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='appointments')
    schedule = models.ForeignKey('Schedule', on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Amount in LKR
    channel_no = models.IntegerField(null=True, blank=True) 
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="appointments", null=True, blank=True)
    invoice_number = models.IntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField(blank=True, null=True, max_length=20)

    class Meta:
        unique_together = ('branch', 'invoice_number')


    def save(self, *args, **kwargs):
        if self.invoice_number is None and self.branch:
            for _ in range(5):  # retry up to 5 times
                try:
                    with transaction.atomic():
                        max_id = Appointment.objects.select_for_update().filter(
                            branch=self.branch
                        ).aggregate(Max('invoice_number'))['invoice_number__max']
                        self.invoice_number = (max_id or 0) + 1
                        super().save(*args, **kwargs)
                    break
                except IntegrityError:
                    continue
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Appointment with {self.doctor} for {self.patient} on {self.date} at {self.time}"
    
    def get_total_paid(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or 0

    def get_remaining_amount(self):
        return float(self.total_fee) - self.get_total_paid()


class ChannelPayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
        ('online_transfer', 'Online Transfer'),
    ]

    appointment = models.ForeignKey('Appointment', on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    is_final = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.appointment.id} - {self.amount} ({self.payment_method})"
    
class OtherItemStock(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="other_item_stocks", null=True, blank=True)
    other_item = models.ForeignKey(OtherItem, on_delete=models.CASCADE, related_name="stocks")
    initial_count = models.PositiveIntegerField()
    qty = models.PositiveIntegerField()
    limit = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.other_item.name} - Initial: {self.initial_count}, Current: {self.qty} "
    
class UserBranch(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="user_branches")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="branch_users")  # ✅ Fixed related_name
    assigned_at = models.DateTimeField(auto_now_add=True)  # Timestamp when assigned

    class Meta:
        unique_together = ('user', 'branch')  # Prevents duplicate user-branch assignments

    def __str__(self):
        return f"{self.user.username} - {self.branch.name}"
    

class ExpenseMainCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ExpenseSubCategory(models.Model):
    main_category = models.ForeignKey(ExpenseMainCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['main_category', 'name']

    def __str__(self):
        return f"{self.main_category.name} > {self.name}"


class Expense(models.Model):
    SOURCE_CHOICES = [
    ('safe', 'Safe'),
    ('cash', 'Cash'),
    ('bank', 'Bank'),
    ]
    paid_source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    main_category = models.ForeignKey(ExpenseMainCategory, on_delete=models.CASCADE)
    sub_category = models.ForeignKey(ExpenseSubCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True)
    paid_from_safe = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True)

class OtherIncomeCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class OtherIncome(models.Model):
    date = models.DateField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    category = models.ForeignKey(OtherIncomeCategory, on_delete=models.PROTECT, related_name="other_incomes")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.name} - LKR {self.amount}"
    
class BusSystemSetting(models.Model):
    title = models.CharField(max_length=200, unique=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)  # Track if this title is currently active

    def __str__(self):
        return self.title
    
class SafeBalance(models.Model):
    branch = models.OneToOneField("Branch", on_delete=models.CASCADE, related_name="safe_balance")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.branch.branch_name} Safe – LKR {self.balance}"
    
class SafeTransaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense'
        DEPOSIT = 'deposit', 'Bank Deposit'

    branch = models.ForeignKey("Branch", on_delete=models.CASCADE, related_name="safe_transactions")
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True, null=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)  # Optional: links to invoice/expense/etc.
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.branch.branch_name} – {self.transaction_type} – LKR {self.amount} on {self.date}"


class DoctorClaimInvoice(models.Model):
    invoice_number = models.CharField(max_length=20, unique=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey("Branch", on_delete=models.CASCADE, related_name="doctor_claim_invoices")
    
    def __str__(self):
        return f"{self.invoice_number} on {self.date}"

class DoctorClaimChannel(models.Model):
    invoice_number = models.CharField(max_length=20,)  
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey("Branch", on_delete=models.CASCADE, related_name="doctor_claim_channels")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="doctor_claim_channels")

    def __str__(self):
        return f"{self.invoice_number} on {self.date}"

    
