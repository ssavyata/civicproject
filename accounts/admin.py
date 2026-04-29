from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'ward_number', 'department')
    list_filter = ('role', 'ward_number')
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info' , {'fields': ('role', 'phone_number', 'ward_number', 'department')}),
    )