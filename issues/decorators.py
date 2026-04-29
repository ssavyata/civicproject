from django.shortcuts import redirect

def citizen_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_citizen():
            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')
    return wrapper

def officer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_officer():
            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')
    return wrapper