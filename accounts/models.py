from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.utils import timezone
from datetime import timedelta
from civicproject import settings
import random

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
    
class UserActivityLog(models.Model):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs')
    login_time   = models.DateTimeField(null=True, blank=True)
    logout_time  = models.DateTimeField(null=True, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    device       = models.CharField(max_length=300, blank=True)
    session_key  = models.CharField(max_length=40, blank=True, db_index=True)

    class Meta:
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user} — logged in {self.login_time}"

    @property
    def duration(self):
        if self.login_time and self.logout_time:
            delta = self.logout_time - self.login_time
            total = int(delta.total_seconds())
            h, remainder = divmod(total, 3600)
            m, s = divmod(remainder, 60)
            if h:
                return f"{h}h {m}m"
            elif m:
                return f"{m}m {s}s"
            else:
                return f"{s}s"
        return "Active"
    


