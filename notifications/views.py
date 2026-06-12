from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notification

# Create your views here.

@login_required
def notifications(request):
<<<<<<< Updated upstream
     notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
     notifs.update(is_read=True)
     return render(request, 'issues/notifications.html', {'notifications': notifs})  
=======
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'citizen/notifications.html', {'notifications': notifs})

@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    if notif.issue:
        return redirect('issue_detail', issue_id=notif.issue.pk)
    return redirect('notifications')

@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    next_url = request.GET.get('next', 'notifications')
    return redirect(next_url)
>>>>>>> Stashed changes
