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
    
    
