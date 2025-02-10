from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework.authtoken.models import Token as BaseToken
from django.utils.translation import gettext_lazy as _

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
    
#refractions
class Refraction(models.Model):
    customer_full_name = models.CharField(max_length=255)
    customer_mobile = models.CharField(max_length=15)
    refraction_number = models.CharField(max_length=10, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate refraction_number automatically if not set
        if not self.refraction_number:
            last_refraction = Refraction.objects.all().order_by('-id').first()
            if last_refraction:
                last_number = int(last_refraction.refraction_number)
                new_number = str(last_number + 1).zfill(3)
            else:
                new_number = "000"  # Starting number
            self.refraction_number = new_number
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_full_name} - {self.refraction_number}"
    
class Patient(models.Model):
    name = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True)
    address = models.TextField(null=True, blank=True)
    nic = models.CharField(max_length=15, unique=True, null=True, blank=True)
    refraction = models.ForeignKey(
        Refraction, null=True, blank=True, on_delete=models.SET_NULL, related_name="patients"
    )  # ✅ Added refraction_id (nullable)

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

    remark = models.CharField(max_length=20, blank=True, null=True)

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

    def __str__(self):
        return self.name
    
class LensCleanerStock(models.Model):
    lens_cleaner = models.ForeignKey(LensCleaner, related_name='stocks', on_delete=models.CASCADE)
    initial_count = models.IntegerField(null=True, blank=True)  # Allows NULL for optional initial stock
    qty = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.lens_cleaner.name} - Qty: {self.qty}"
    
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(Patient, related_name='orders', on_delete=models.CASCADE)
    refraction = models.ForeignKey(Refraction, null=True, blank=True, on_delete=models.SET_NULL)
    order_date = models.DateTimeField(auto_now_add=True)
    order_updated_date = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    sales_staff_code = models.ForeignKey(CustomUser,related_name='orders',on_delete=models.CASCADE, null=True, blank=True)
    remark = models.TextField(null=True, blank=True)  # New field

    def __str__(self):
        return f"Order {self.id} - Status: {self.status} - Customer: {self.customer.id}"
    
class Invoice(models.Model):
    INVOICE_TYPES = [
        ('factory', 'Factory Invoice'),  # Linked to an order with refraction
        ('manual', 'Manual Invoice')  # Linked to an order without refraction
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_type = models.CharField(max_length=10, choices=INVOICE_TYPES)  # ✅ Identifies invoice type
    daily_invoice_no = models.IntegerField(null=True, blank=True)  # ✅ Factory invoices get a daily number
    invoice_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['invoice_date', 'daily_invoice_no']  # Ensures daily numbering uniqueness

    def save(self, *args, **kwargs):
        """ Auto-generate `daily_invoice_no` for factory invoices per day """
        if self.invoice_type == 'factory' and not self.daily_invoice_no:
            today_count = Invoice.objects.filter(
                invoice_type='factory',
                invoice_date__date=self.invoice_date.date()
            ).count()
            self.daily_invoice_no = today_count + 1  # Start from 1 each day
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.id} - {self.invoice_type} - Order {self.order.id}"

    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    lens = models.ForeignKey(Lens, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    lens_cleaner = models.ForeignKey(LensCleaner, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    frame = models.ForeignKey(Frame, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

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
    date = models.DateField()
    start_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.AVAILABLE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Appointment with {self.doctor} for {self.patient} on {self.date} at {self.time}"

class ChannelPayment(models.Model):
    class PaymentMethods(models.TextChoices):
        CASH = 'Cash', 'Cash'
        CARD = 'Card', 'Card'

    appointment = models.ForeignKey('Appointment', on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PaymentMethods.choices)
    is_final = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.appointment.id} - {self.amount} ({self.payment_method})"

