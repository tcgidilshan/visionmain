from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework.authtoken.models import Token as BaseToken

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
    
class RefractionDetails(models.Model):
    refraction = models.OneToOneField(
        Refraction, on_delete=models.CASCADE, related_name="details"
    )
    hb_rx_right = models.CharField(max_length=10, blank=True, null=True)  # Right Eye Hb Rx
    hb_rx_left = models.CharField(max_length=10, blank=True, null=True)   # Left Eye Hb Rx

    auto_ref = models.CharField(max_length=20, blank=True, null=True)
    ntc = models.CharField(max_length=10, blank=True, null=True)
    va_without_glass = models.CharField(max_length=10, blank=True, null=True)
    va_without_ph = models.CharField(max_length=10, blank=True, null=True)
    va_with_glass = models.CharField(max_length=10, blank=True, null=True)

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
        return f"Details for {self.refraction.customer_full_name}"
    
#brands
class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    
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

    def __str__(self):
        return f"Frame: {self.frame.id} - Qty: {self.qty}"