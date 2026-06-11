from .models import Notification

def notify(user, title, message, notif_type='general', issue=None):
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notif_type=notif_type,
        issue=issue,
    )