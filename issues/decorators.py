from django.shortcuts import redirect
from functools import wraps

def citizen_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_admin():
            return redirect('admin_dashboard')
        if request.user.is_officer():
            return redirect('officer_dashboard')
        if request.user.is_citizen():
            return view_func(request, *args, **kwargs)
        return redirect('login')
    return wrapper

def officer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_admin():
            return redirect('admin_dashboard')
        if request.user.is_citizen():
            return redirect('citizen_dashboard')
        if request.user.is_officer():
            return view_func(request, *args, **kwargs)
        return redirect('login')
    return wrapper