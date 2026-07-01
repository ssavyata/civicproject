from allauth.account.models import EmailAddress
from allauth.account.views import ConfirmEmailView
from openai import base_url
from accounts.models import UserActivityLog
from datetime import date
from .decorators import user_not_authenticated
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.mail import EmailMessage, send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.sites.models import Site
from django.db.models import Subquery, OuterRef
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .forms import CitizenRegistrationForm
from httpx import request
from .models import User
from .tokens import account_activation_token
from urllib import request
import json
import requests
import random

@user_not_authenticated
def register(request):
    if request.method == 'POST':
        form = CitizenRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'citizen'
            user.ward_number = 12
            user.is_active = False
            user.save()
            
            activateEmail(request, user, form.cleaned_data.get('email'))
            
            return render(request, 'register.html', {'form': form, 'email_sent': True})
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CitizenRegistrationForm()

    return render(request, 'register.html', {'form': form})


def activateEmail(request, user, to_email):
    mail_subject = 'Activate your CivicReport Account'
    
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    
    # Build the link using settings — works on any host
    base_url = getattr(settings, 'FRONTEND_URL', None) or \
           f"{'https' if request.is_secure() else 'http'}://{request.get_host()}"
    
    activation_path = reverse('activate', kwargs={'uidb64': uid, 'token': token})
    activation_link = f"{base_url}{activation_path}"
    
    message = render_to_string('activate_account.html', {
        'user': user.username,
        'activation_link': activation_link,
    })
    
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f'Activation link sent to {to_email}. Check your spam folder too.')
    else:
        messages.error(request, f'Could not send email to {to_email}. Please check the address.')

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        EmailAddress.objects.filter(user=user).update(verified=True, primary=True)
        # Render a thank-you page with auto-redirect
        return render(request, 'activation_success.html', {'username': user.username})
    else:
        messages.error(request, 'Activation link is invalid or has expired.')
        return redirect('register')

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')  
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, 'Please verify your email before logging in.')
                return render(request, 'login.html', {})

            login(request, user)

            if user.is_admin():
                return redirect('admin_dashboard')
            elif user.is_officer():
                return redirect('officer_dashboard')
            else:
                return redirect('citizen_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


def user_logout(request):
    logout(request) 
    return redirect('login')


@login_required
def dashboard_home(request):
    user = request.user
    is_social = user.socialaccount_set.exists()
    is_email_verified = EmailAddress.objects.filter(user=user, verified=True).exists()

    if not is_social and not is_email_verified:
        return redirect('account_email_verification_sent')

    return render(request, 'dashboard.html')

def activity_log_view(request):
    username_filter = request.GET.get('username', '').strip()
    status_filter   = request.GET.get('status', '')

    logs = (
        UserActivityLog.objects
        .select_related('user')
        .exclude(user__role='admin')
        .order_by('user', '-login_time')
        .distinct('user')         
    )

    latest_ids = (
        UserActivityLog.objects
        .exclude(user__role='admin')
        .order_by('user_id', '-login_time')
        .distinct('user_id')
        .values('id')
    )

    logs = UserActivityLog.objects.filter(id__in=Subquery(latest_ids)).select_related('user').order_by('-login_time')

    if username_filter:
        logs = logs.filter(user__username__icontains=username_filter)

    if status_filter == 'active':
        logs = logs.filter(logout_time__isnull=True)
    elif status_filter == 'ended':
        logs = logs.filter(logout_time__isnull=False)

    paginator = Paginator(logs, 20)
    logs_page = paginator.get_page(request.GET.get('page'))

    non_admin_logs = UserActivityLog.objects.exclude(user__role='admin')

    context = {
        'logs':            logs_page,
        'total_count':     non_admin_logs.values('user').distinct().count(),  # unique users, not sessions
        'active_now':      non_admin_logs.filter(logout_time__isnull=True).values('user').distinct().count(),
        'sessions_today':  non_admin_logs.filter(login_time__date=date.today()).values('user').distinct().count(),
        'username_filter': username_filter,
        'status_filter':   status_filter,
    }
    return render(request, 'admin/activity_log.html', context)


@login_required
@csrf_exempt  
def ai_describe_proxy(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY  

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    return JsonResponse(response.json(), status=response.status_code)