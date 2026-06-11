from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import UserActivityLog


def get_device(request):
    ua = request.META.get('HTTP_USER_AGENT', '')

    if 'Mobile' in ua or 'Android' in ua:
        device_type = 'Mobile'
    elif 'iPad' in ua:
        device_type = 'Tablet'
    else:
        device_type = 'Desktop'

    if 'Edg' in ua:       browser = 'Edge'
    elif 'Chrome' in ua:  browser = 'Chrome'
    elif 'Firefox' in ua: browser = 'Firefox'
    elif 'Safari' in ua:  browser = 'Safari'
    else:                 browser = 'Unknown Browser'

    if 'Windows' in ua:     os_name = 'Windows'
    elif 'Macintosh' in ua: os_name = 'Mac'
    elif 'Android' in ua:   os_name = 'Android'
    elif 'iPhone' in ua:    os_name = 'iOS'
    elif 'Linux' in ua:     os_name = 'Linux'
    else:                   os_name = 'Unknown OS'

    return f"{device_type} · {browser} · {os_name}"


def get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    # Close any previously open sessions for this user first
    UserActivityLog.objects.filter(
        user=user,
        logout_time__isnull=True
    ).update(logout_time=timezone.now())

    # Create a fresh session record
    UserActivityLog.objects.create(
        user=user,
        login_time=timezone.now(),
        ip_address=get_ip(request),
        device=get_device(request),
        session_key=request.session.session_key or '',
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user:
        log = UserActivityLog.objects.filter(
            user=user,
            session_key=request.session.session_key,
            logout_time__isnull=True
        ).first()
        if log:
            log.logout_time = timezone.now()
            log.save()