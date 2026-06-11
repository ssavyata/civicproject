from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIF_TYPES = [
        ('issue_submitted', 'Issue Submitted'),
        ('status_changed',  'Status Changed'),
        ('issue_assigned',  'Issue Assigned'),
        ('issue_resolved',  'Issue Resolved'),
        ('issue_rejected',  'Issue Rejected'),
        ('remark_added',    'Remark Added'),
        ('general',         'General'),
    ]

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    issue      = models.ForeignKey(
        'issues.Issue',
        on_delete=models.CASCADE,
        null=True, blank=True,
    )
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPES, default='general')
    title      = models.CharField(max_length=255, default='')
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}"