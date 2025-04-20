from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework.authtoken.models import Token as BaseToken
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction

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
    phone_number = models.CharField(null=True, blank=True,max_length=15, unique=True)
    address = models.TextField(null=True, blank=True)
    nic = models.CharField(max_length=15, unique=True, null=True, blank=True)
    refraction = models.ForeignKey(
        Refraction, null=True, blank=True, on_delete=models.SET_NULL, related_name="patients"
    )  #  Added refraction_id (nullable)
    #new feature
    patient_note=models.CharField(max_length=100,null=True,blank=True)
    def __str__(self):
        return f"{self.name}"
    
class RefractionDetails(models.Model):
    refraction = models.OneToOneField(
        Refraction, on_delete=models.CASCADE, related_name="refraction_details",blank=True, null=True
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="refraction_details", blank=True, null=True
    )
    is_manual = models.BooleanField(default=False) 
    # Hb Rx
    hb_rx_right_dist = models.CharField(max_length=10, blank=True, null=True)  # Right Eye Hb Rx Dist
    hb_rx_left_dist = models.CharField(max_length=10, blank=True, null=True)   # Left Eye Hb Rx Dist
    hb_rx_right_near = models.CharField(max_length=10, blank=True, null=True)  # Right Eye Hb Rx Near
    hb_rx_left_near = models.CharField(max_length=10, blank=True, null=True)   # Left Eye Hb Rx Near

    # Auto Ref
    auto_ref_right = models.CharField(max_length=20, blank=True, null=True)  # Auto Ref Right
    auto_ref_left = models.CharField(max_length=20, blank=True, null=True)   # Auto Ref Left

    # NTC
    ntc_right = models.CharField(max_length=10, blank=True, null=True)  # NTC Right
    ntc_left = models.CharField(max_length=10, blank=True, null=True)   # NTC Left

    # VA Without Glass
    va_without_glass_right = models.CharField(max_length=10, blank=True, null=True)  # VA Without Glass Right
    va_without_glass_left = models.CharField(max_length=10, blank=True, null=True)   # VA Without Glass Left

    # VA Without P/H
    va_without_ph_right = models.CharField(max_length=10, blank=True, null=True)  # VA Without P/H Right
    va_without_ph_left = models.CharField(max_length=10, blank=True, null=True)   # VA Without P/H Left

    # VA With Glass
    va_with_glass_right = models.CharField(max_length=10, blank=True, null=True)  # VA With Glass Right
    va_with_glass_left = models.CharField(max_length=10, blank=True, null=True)   # VA With Glass Left

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
    prescription = models.BooleanField(default=False)
    cataract = models.BooleanField(default=False)
    refraction_remark = models.CharField(max_length=100, blank=True, null=True)
    shuger=models.BooleanField(default=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,  
        null=True,
        blank=True,
        related_name="refraction_details",
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
    brand = models.ForeignKey(Brand, related_name='frames', on_delete=models.CASCADE)
    code = models.ForeignKey(Code, related_name='frames', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, related_name='frames', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=50)
    species = models.CharField(max_length=100)
    image = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.brand.name} - {self.code.name} - {self.color.name}"
    
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
    
class Lens(models.Model):
    type = models.ForeignKey(LenseType, related_name='lenses', on_delete=models.CASCADE)
    coating = models.ForeignKey(Coating, related_name='lenses', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name='lenses', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)

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
    def __str__(self):
        return f"Order {self.id} - Status: {self.status} - Customer: {self.customer.id}"
    
class ExternalLens(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="external_lenses", null=True, blank=True)
    type = models.ForeignKey(LenseType, related_name='external_lenses', on_delete=models.CASCADE)
    coating = models.ForeignKey(Coating, related_name='external_lenses', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name='external_lenses', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # ✅ Manually entered price

    def __str__(self):
        return f"{self.brand.name} {self.type.name} ({self.coating.name}) - LKR {self.price}"
    
class ExternalLensPower(models.Model):
    SIDE_CHOICES = [
        ('left', 'Left'),
        ('right', 'Right'),
    ]
    external_lens = models.ForeignKey(ExternalLens, related_name='external_lens_powers', on_delete=models.CASCADE)
    power = models.ForeignKey('Power', related_name='external_lens_powers', on_delete=models.CASCADE)  # Assuming Power table exists
    value = models.DecimalField(max_digits=5, decimal_places=2,)
    side = models.CharField(
        max_length=10,
        choices=SIDE_CHOICES,
        null=True, 
        blank=True 
    )

    def __str__(self):
        return f"Lens: {self.external_lens} - Power: {self.value} ({self.side})"
    
class Invoice(models.Model):
    INVOICE_TYPES = [
        ('factory', 'Factory Invoice'),  # Linked to an order with refraction
        ('manual', 'Manual Invoice')  # Linked to an order without refraction
    ]

    progress_status = models.CharField(
        max_length=30,
        choices=[
            ('received_from_customer', 'Received from Customer'),
            ('issue_to_factory', 'Issued to Factory'),
            ('received_from_factory', 'Received from Factory'),
            ('issue_to_customer', 'Issued to Customer'),
        ],
        default='received_from_customer'
    )

    lens_arrival_status = models.CharField(
        max_length=20,
        choices=[('received', 'Received'), ('not_received', 'Not Received')],
        null=True, blank=True
    )

    whatsapp_sent = models.BooleanField(default=False)

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_type = models.CharField(max_length=10, choices=INVOICE_TYPES)  #  Identifies invoice type
    daily_invoice_no = models.CharField(max_length=10,null=True, blank=True)  #  Factory invoices get a daily number
    invoice_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    invoice_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['invoice_date', 'daily_invoice_no']  # Ensures daily numbering uniqueness
        constraints = [
            models.UniqueConstraint(fields=["invoice_number"], name="unique_invoice_number")
        ]

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

    def save(self, *args, **kwargs):
       # Dynamically calculate subtotal on save
       self.subtotal = self.quantity * self.price_per_unit
       super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order.id} Item - Subtotal: {self.subtotal}"
    
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

    def __str__(self):
        return f"Payment for Order {self.order.id} - Amount: {self.amount}"
    
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Appointment with {self.doctor} for {self.patient} on {self.date} at {self.time}"

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
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    main_category = models.ForeignKey(ExpenseMainCategory, on_delete=models.CASCADE)
    sub_category = models.ForeignKey(ExpenseSubCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    
