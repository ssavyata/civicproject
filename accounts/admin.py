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

from django.contrib import admin
from .models import UserActivityLog

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display   = ('user', 'login_time', 'logout_time', 'ip_address', 'device')
    list_filter    = ('login_time',)
    search_fields  = ('user__username', 'ip_address', 'device')
    readonly_fields = ('user', 'login_time', 'logout_time', 'ip_address', 'device', 'session_key')
    ordering       = ('-login_time',)