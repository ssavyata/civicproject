from notifications.models import Notification

def unread_notifications(request):
    if request.user.is_authenticated:
        notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {
            'unread_count': unread_count,
            'notifications': notifs,
        }
    return {'unread_count': 0, 'notifications': []}