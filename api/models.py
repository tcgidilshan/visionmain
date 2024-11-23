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

# class CustomUser(AbstractUser):
#     mobile = models.CharField(max_length=15, blank=True, null=True) 
#     groups = models.ManyToManyField(
#         Group,
#         related_name="customuser_groups",  # Avoid conflict
#         blank=True,
#     )
#     user_permissions = models.ManyToManyField(
#         Permission,
#         related_name="customuser_permissions",  # Avoid conflict
#         blank=True,
#     )
    
class Branch(models.Model):
    branch_name = models.CharField(max_length=255)  # Name of the branch
    location = models.TextField()  # Branch location (address or details)
    created_at = models.DateTimeField(auto_now_add=True)  # Auto-created timestamp
    updated_at = models.DateTimeField(auto_now=True)  # Auto-updated timestamp

    def __str__(self):
        return self.branch_name
    
    
