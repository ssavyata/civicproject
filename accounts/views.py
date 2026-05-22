from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib import messages
from .models import User, LoginOTP
from django.contrib.auth.decorators import login_required
from .decorators import user_not_authenticated
from .forms import CitizenRegistrationForm
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage, send_mail
from .tokens import account_activation_token
from allauth.account.models import EmailAddress
from allauth.account.views import ConfirmEmailView
import random

# Core configuration utilities
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site


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
            
            # ✅ Sends token correctly to matching snake_case utility
            activate_email(request, user, form.cleaned_data.get('email'))
            
            return render(request, 'register.html', {'form': form, 'email_sent': True})
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CitizenRegistrationForm()

    return render(request, 'register.html', {'form': form})


def activate_email(request, user, to_email):
    mail_subject = 'Activate your account'
    message = render_to_string('activate_account.html', {
        'user': user,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'http' if settings.DEBUG else 'https',
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    email.send()

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

        # ✅ FIX 2: Also verify the allauth EmailAddress record so allauth doesn't block login
        EmailAddress.objects.filter(user=user).update(verified=True, primary=True)

        messages.success(request, 'Email confirmed! Your account is now active. Please log in.')
        return redirect('login')
    else:
        messages.error(request, 'Activation link is invalid or has expired.')
        return redirect('register')  # ✅ FIX 3: Send back to register, not login, on failure



def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')  # ✅ FIX 4: Use .get() to avoid KeyError
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                # ✅ FIX 5: Show error and stop — don't redirect to dashboard if inactive
                messages.error(request, 'Please verify your email before logging in.')
                return render(request, 'login.html')

            login(request, user)

            # ✅ FIX 6: Redirect based on role AFTER login
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


def custom_login_step_one(request):
    if request.method == 'POST':
        login_input = request.POST.get('login')
        password_input = request.POST.get('password')

        if not login_input or not password_input:
            return render(request, 'account/login.html', {'error': 'Please fill in all fields.'})

        if '@' in login_input:
            user_obj = User.objects.filter(email=login_input).first()
        else:
            user_obj = User.objects.filter(username=login_input).first()

        # ✅ FIX 7: Check is_active before sending OTP
        if user_obj and user_obj.check_password(password_input):
            if not user_obj.is_active:
                return render(request, 'account/login.html', {
                    'error': 'Please verify your email before logging in.'
                })

            otp_code = f"{random.randint(100000, 999999)}"
            # ✅ FIX 8: Delete old OTPs for this user before creating a new one
            LoginOTP.objects.filter(user=user_obj).delete()
            LoginOTP.objects.create(user=user_obj, code=otp_code)

            send_mail(
                'Your Login Verification Code',
                f'Your verification code is: {otp_code}',
                'noreply@yourdomain.com',
                [user_obj.email],
                fail_silently=False,
            )

            request.session['otp_user_id'] = user_obj.id
            return redirect('verify_login_otp')
        else:
            return render(request, 'account/login.html', {'error': 'Invalid credentials.'})

    return render(request, 'account/login.html')


def verify_login_otp(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('custom_login_step_one')

    if request.method == 'POST':
        entered_code = request.POST.get('otp_code')
        otp_record = LoginOTP.objects.filter(user_id=user_id, code=entered_code).last()

        if otp_record and otp_record.is_valid():
            user = otp_record.user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            del request.session['otp_user_id']
            otp_record.delete()

            # ✅ FIX 9: Redirect based on role instead of hardcoded 'dashboard'
            if user.is_admin():
                return redirect('admin_dashboard')
            elif user.is_officer():
                return redirect('officer_dashboard')
            else:
                return redirect('citizen_dashboard')
        else:
            return render(request, 'account/verify_otp.html', {'error': 'Invalid or expired code.'})

    return render(request, 'account/verify_otp.html')

class CustomConfirmEmailView(ConfirmEmailView):
    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        messages.success(self.request, 'Your email has been confirmed! You can now log in.')
        return redirect('login')