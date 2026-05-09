from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login, logout

from django.contrib import messages
from .models import User
from django.contrib.auth.decorators import login_required
from .forms import CitizenRegistrationForm

# Create your views here.

def register(request):
    if request.method == 'POST':
        form = CitizenRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'citizen'
            user.ward_number = 12  # ← fixed to Ward 12
            user.save()
            login(request, user)
            messages.success(request, 'Account created! Welcome to CivicReport Ward 12.')
            return redirect('citizen_dashboard')
    else:
        form = CitizenRegistrationForm()

    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
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


