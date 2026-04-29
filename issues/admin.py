from django.contrib import admin
from .models import Department, Issue, Feedback

# Register your models here.

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    
@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'citizen', 'assigned_department', 'assigned_officer', 'submitted_at')
    list_filter = ('status', 'category', 'ward_number', 'assigned_department')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('submitted_at', 'updated_at')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('issue', 'citizen', 'rating', 'submitted_at')
    
