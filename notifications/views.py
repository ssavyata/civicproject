from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notification

# Create your views here.

@login_required
def notifications(request):
     notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
     notifs.update(is_read=True)
     return render(request, 'issues/notifications.html', {'notifications': notifs})  
