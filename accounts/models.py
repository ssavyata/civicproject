from django.db import models
from django.contrib.auth.models import AbstractUser
import random
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class User(AbstractUser):
    ROLE_CHOICES = [
        ('citizen', 'Citizen'),
        ('officer', 'Department Officer'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    ward_number = models.IntegerField(default=1)


    department = models.ForeignKey(
        'issues.Department',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='officers'
    )

    def is_citizen(self):
        return self.role == 'citizen'
    
    def is_officer(self):
        return self.role == 'officer'
    
    def is_admin(self):
        return self.role == 'admin'

class LoginOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        # Code expires after 5 minutes
        return timezone.now() < self.created_at + timedelta(minutes=5)
