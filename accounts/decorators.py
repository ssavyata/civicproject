from django.shortcuts import render,redirect

def user_not_authenticated(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_admin():
                return redirect('admin_dashboard')
            elif request.user.is_officer():
                return redirect('officer_dashboard')
            else:
                return redirect('citizen_dashboard')
        else:
            return view_func(request, *args, **kwargs)
    return wrapper