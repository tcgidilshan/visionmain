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
from django.utils.timezone import now
from .services.image_uploard_service import compress_image_to_webp
import uuid

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
    is_confirmed = models.BooleanField(default=False)  # For "ticking" confirmed deposits
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
    customer_mobile = models.CharField(max_length=15,blank=True,null=True)
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
    

class RefractionDetailsAuditLog(models.Model):
    refraction_details = models.ForeignKey(
        RefractionDetails,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refraction_details_audit_logs_as_user'
    )
    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refraction_details_audit_logs_as_admin'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.field_name} changed by {self.modified_by} on {self.modified_at}"

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
    class Meta:
        unique_together = (
            'brand',
            'name'
        )    

class FrameImage(models.Model):
    def get_upload_path(instance, filename):
        # This will create a path like: frame_images/<uuid>/<filename>
        return f'frame_images/{instance.uuid}/{filename}'
        
    image = models.ImageField(upload_to=get_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return f"Image {self.id}"
        
    def save(self, *args, **kwargs):
        # Generate UUID first if it's a new instance
        if not self.uuid:
            self.uuid = uuid.uuid4()
            
        # Handle image conversion and compression
        if self.image and hasattr(self.image, 'file') and not str(self.image).endswith('.webp'):
            new_image = compress_image_to_webp(self.image)
            if new_image:
                self.image.save(new_image.name, new_image, save=False)
        super().save(*args, **kwargs)

class OrderImage(models.Model):
    def get_upload_path(instance, filename):
        # This will create a path like: order_images/<uuid>/<filename>
        return f'order_images/{instance.uuid}/{filename}'
        
    image = models.ImageField(upload_to=get_upload_path)
    order = models.ForeignKey('Order', related_name='order_images', on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return f"Image {self.id}"
        
    def save(self, *args, **kwargs):
        # Generate UUID first if it's a new instance
        if not self.uuid:
            self.uuid = uuid.uuid4()
            
        # Handle image conversion and compression
        if self.image and hasattr(self.image, 'file') and not str(self.image).endswith('.webp'):
            new_image = compress_image_to_webp(self.image)
            if new_image:
                self.image.save(new_image.name, new_image, save=False)
        super().save(*args, **kwargs)

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
    is_active = models.BooleanField(default=True) 
    image = models.ForeignKey(FrameImage, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"{self.brand.name} - {self.code.name} - {self.color.name} - {self.get_brand_type_display()}"
    class Meta:
        unique_together = (
            'brand',
            'code',
            'color',
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

class FrameStockHistory(models.Model):
    ADD = 'add'
    TRANSFER = 'transfer'
    REMOVE = 'remove'

    ACTION_CHOICES = [
        (ADD, 'Add'),
        (TRANSFER, 'Transfer'),
        (REMOVE, 'Remove'),
    ]
    frame = models.ForeignKey('Frame', on_delete=models.CASCADE, related_name='stock_histories')
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='branch_frame_stock')
    transfer_to = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='frame_stock_transfers', null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    quantity_changed = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # performed_by = models.ForeignKey(CustomUser,related_name='stock_histories',on_delete=models.CASCADE, null=True, blank=True)
    # note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.action.upper()} {self.quantity_changed} of {self.frame} at {self.branch}"
class LensStockHistory(models.Model):
    ADD = 'add'
    TRANSFER = 'transfer'
    REMOVE = 'remove'

    ACTION_CHOICES = [
        (ADD, 'Add'),
        (TRANSFER, 'Transfer'),
        (REMOVE, 'Remove'),
    ]
    lens = models.ForeignKey('Lens', on_delete=models.CASCADE, related_name='stock_histories')
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='lens_stock_histories')  # Changed related_name
    transfer_to = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='lens_stock_transfers', null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    quantity_changed = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # performed_by = models.ForeignKey(CustomUser, related_name='lens_stock_histories', on_delete=models.CASCADE, null=True, blank=True)
    # note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.action.upper()} {self.quantity_changed} of {self.lens} at {self.branch}"
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
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    FITTING_CHOICES = [
        ('pending', 'Pending'),
        ('fitting_ok', 'Fitting Ok'),
        ('not_fitting', 'Not Fitting'),
        ('damage', 'Damage'),
    
    ]
    urgent=models.BooleanField(default=False)
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

    pd = models.CharField(max_length=5, null=True, blank=True)
    height = models.CharField(max_length=5, null=True, blank=True)
    right_height = models.CharField(max_length=5, null=True, blank=True)
    left_height = models.CharField(max_length=5, null=True, blank=True)
    left_pd = models.CharField(max_length=5, null=True, blank=True)
    right_pd = models.CharField(max_length=5, null=True, blank=True)


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
    is_refund = models.BooleanField(default=False)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_note = models.TextField(blank=True, null=True)
    issued_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_orders'
    )
    issued_date = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    fitting_status = models.CharField(max_length=20, choices=FITTING_CHOICES, default='Pending')
    fitting_status_updated_date = models.DateTimeField(null=True, blank=True)
    objects = SoftDeleteManager()      # Only active records
    all_objects = models.Manager() 

    def __str__(self):
        return f"Order {self.id} - Status: {self.status} - Customer: {self.customer.id}"
    
    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    def save(self, *args, **kwargs):
        if self.pk:
            # Fetch the original from the database
            orig = Order.all_objects.filter(pk=self.pk).first()
            # Only update the timestamp if status actually changed
            if orig and orig.fitting_status != self.fitting_status:
                self.fitting_status_updated_date = timezone.now()
               # If issued_by was previously None and is now set, or issued_by changes
            if orig and orig.issued_by != self.issued_by and self.issued_by is not None:
                self.issued_date = timezone.now()
        else:
            # On create, set timestamp if not already set
            if not self.fitting_status_updated_date:
                self.fitting_status_updated_date = timezone.now()

            # On create, set issued_date only if issued_by is set at creation
            if self.issued_by is not None:
                self.issued_date = timezone.now()   
        super().save(*args, **kwargs)

class OrderAuditLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_audit_logs')
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_audit_logs_as_user'
    )
    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_audit_logs_as_admin'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.field_name} changed from {self.old_value} to {self.new_value}"
class OrderProgress(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_progress_status')
    progress_status = models.CharField(
        max_length=30,
        choices=[
            ('received_from_customer', 'Received from Customer'),
            ('issue_to_factory', 'Issued to Factory'),
            ('received_from_factory', 'Received from Factory'),
            ('issue_to_customer', 'Issued to Customer'),
        ]
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['changed_at']
    
    def __str__(self):
        return f"Order {self.order.id} - {self.progress_status} at {self.changed_at}"

class ArrivalStatus(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='arrival_status')
    arrival_status = models.CharField(
        max_length=30,
        choices=[
            ('mnt_marked', 'Mnt Marked'),
            ('recived', 'Recived'),
        ],
        default='recived'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Order {self.order.id} - {self.arrival_status} at {self.created_at}"

class MntOrder(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='mnt_orders'
    )  # Links to the original factory order
    mnt_number = models.CharField(
        max_length=20
    )  # E.g. "MNT0001", unique per order
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mnt_orders_user'
    )
    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mnt_orders_admin'
    )
    mnt_price= models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Price for MNT order
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='mnt_orders_branch',
        null=False,
        blank=False 
    )

    class Meta:
        unique_together = ('order', 'mnt_number','branch')
        ordering = ['created_at']

    def __str__(self):
        return f"MNT {self.mnt_number} for Order {self.order.id} ({self.user})"

    def save(self, *args, **kwargs):
        # TODO: Only set on create, not update!
        if not self.mnt_number:
            # Assume branch_code is first 3 letters (customize as needed)
            branch_code = self.branch.branch_name[:3].upper()
            # Count how many MNTs exist for this branch
            last_mnt = MntOrder.objects.filter(branch=self.branch).order_by('-id').first()
            if last_mnt and last_mnt.mnt_number:
                # Extract last numeric part; fallback to 1 if parsing fails
                try:
                    last_num = int(''.join(filter(str.isdigit, last_mnt.mnt_number)))
                    next_num = last_num + 1
                except Exception:
                    next_num = 1
            else:
                next_num = 1
            self.mnt_number = f"MNT{branch_code}{str(next_num).zfill(3)}"
        super().save(*args, **kwargs)

    
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
        if not self.invoice_date:
            self.invoice_date = timezone.now()

        if not self.invoice_number:
            if not self.order or not self.order.branch:
                raise ValueError("Invoice must be linked to an order with a valid branch.")

            # Handle 'normal' invoice type with branch prefix
            if self.invoice_type == 'normal':
                with transaction.atomic():
                    # Get the first 3 letters of branch name in uppercase
                    branch_prefix = self.order.branch.branch_name[:3].upper()
                    
                    # Get the last invoice with 'normal' type for this branch
                    last_invoice = Invoice.all_objects.select_for_update().filter(
                        invoice_type='normal',
                        order__branch=self.order.branch
                    ).order_by('-id').first()

                    if last_invoice and last_invoice.invoice_number and last_invoice.invoice_number.startswith(branch_prefix):
                        try:
                            # Extract the numeric part after branch prefix and increment
                            number_part = last_invoice.invoice_number[4:]  # Skip the 3-letter branch prefix
                            number = int(number_part) + 1
                        except (ValueError, IndexError):
                            number = 1
                    else:
                        number = 1

                    # Format as {BRANCH_PREFIX}N{number} (e.g., COMN001, COMN002)
                    self.invoice_number = f"{branch_prefix}N{number:03d}"
            else:
                # Original logic for other invoice types
                branch_code = self.order.branch.branch_name[:3].upper()
                day_str = self.invoice_date.strftime('%d')  # Last 2 digits for day

                with transaction.atomic():
                    last_invoice = Invoice.all_objects.select_for_update().filter(
                        invoice_type=self.invoice_type,
                        order__branch=self.order.branch
                    ).order_by('-id').first()

                    if last_invoice and last_invoice.invoice_number:
                        try:
                            # Extract padded number between branch_code (3 chars) and day_str (last 2 chars)
                            last_number_part = last_invoice.invoice_number[3:-2]
                            number = int(last_number_part) + 1
                        except Exception:
                            number = 1
                    else:
                        number = 1

                    padded = str(number).zfill(5)
                    self.invoice_number = f"{branch_code}{padded}{day_str}"

        super().save(*args, **kwargs)

class OtherItem(models.Model):
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ${self.price} - {'Active' if self.is_active else 'Inactive'}"
    
class OrderItem(models.Model):
    objects = SoftDeleteManager()
    all_objects = models.Manager()
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
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    # In OrderItem model:
    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_order_items'
    )
    admin = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_order_items'
    )

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
class OrderItemWhatsAppLog(models.Model):
    # Only log when a WhatsApp message is actually sent
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='whatsapp_logs'
    )
    status = models.CharField(max_length=20, choices=[('sent', 'Sent'), ('mnt_marked', 'Mnt Marked')], default='sent')
    created_at = models.DateTimeField(auto_now_add=True)  # When sent

    def __str__(self):
        return f"Order {self.order.id} WhatsApp sent at {self.created_at}"

class OrderPayment(models.Model):
    objects = SoftDeleteManager()
    all_objects = models.Manager()
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
    is_edited = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_order_payments')
    admin = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_order_payments')

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
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      # Only active records
    all_objects = models.Manager() 

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

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
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_refund = models.BooleanField(default=False)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_note = models.TextField(blank=True, null=True)

    objects = SoftDeleteManager()      # Only active records
    all_objects = models.Manager() 
    class Meta:
        unique_together = ('branch', 'invoice_number')

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if self.invoice_number is None and self.branch:
            for _ in range(5):  # retry up to 5 times
                try:
                    with transaction.atomic():
                        # Use all_objects to include soft-deleted records
                        max_id = Appointment.all_objects.select_for_update().filter(
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
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      # Only active records
    all_objects = models.Manager() 

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

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
    is_refund=models.BooleanField(default=False)

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
    
class SolderingOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        READY = 'ready', 'Ready'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    class ProgressStatus(models.TextChoices):
        RECEIVED_FROM_CUSTOMER = 'received_from_customer', 'Received from Customer'
        ISSUE_TO_FACTORY = 'issue_to_factory', 'Issued to Factory'
        RECEIVED_FROM_FACTORY = 'received_from_factory', 'Received from Factory'
        ISSUE_TO_CUSTOMER = 'issue_to_customer', 'Issued to Customer'

    note = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    progress_status = models.CharField(max_length=30, choices=ProgressStatus.choices, default=ProgressStatus.RECEIVED_FROM_CUSTOMER)
    progress_status_updated_at = models.DateTimeField(auto_now=True)
    patient = models.ForeignKey(Patient, related_name='soldering_orders', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.CASCADE,
        related_name='soldering_orders',
        null=True,
        blank=True 
    )
    order_date = models.DateField(auto_now_add=True)
    order_updated_date = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      # Only active payments
    all_objects = models.Manager()     # Include soft-deleted

    def __str__(self):
        return f"Soldering Order #{self.id} for {self.patient}"
    
    def save(self, *args, **kwargs):
        if self.pk:
            orig = SolderingOrder.all_objects.filter(pk=self.pk).first()
            # Compare the original progress_status to the new one
            if orig and orig.progress_status != self.progress_status:
                self.progress_status_updated_at = timezone.now()
        else:
            # On creation, set to now
            self.progress_status_updated_at = timezone.now()
        super().save(*args, **kwargs)

    
class SolderingInvoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(auto_now_add=True)
    order = models.ForeignKey(SolderingOrder, related_name='invoices', on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      # Only active payments
    all_objects = models.Manager()     # Include soft-deleted

    def __str__(self):
        return f"Invoice #{self.invoice_number}"
class SolderingPayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
    ('credit_card', 'Credit Card'),
    ('cash', 'Cash'),
    ('online_transfer', 'Online Transfer'),
]
    class TransactionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    transaction_status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.COMPLETED)
    is_final_payment = models.BooleanField(default=False)
    is_partial = models.BooleanField(default=False)
    order = models.ForeignKey('SolderingOrder', related_name='payments', on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      # Only active payments
    all_objects = models.Manager()     # Include soft-deleted

    def __str__(self):
        return f"Payment #{self.id} - Order #{self.order.id}"
    
class DailyCashInHandRecord(models.Model):
    branch_id = models.IntegerField()
    date = models.DateField()
    cash_in_hand = models.DecimalField(max_digits=10, decimal_places=2)
    before_balance = models.DecimalField(max_digits=10, decimal_places=2)
    today_balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Branch {self.branch_id} - {self.date}: {self.cash_in_hand}"
