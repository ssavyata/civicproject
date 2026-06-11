from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'), 
    path('logout/', views.user_logout, name='logout'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('accounts/login/', views.custom_login_step_one, name='custom_login'),
    path('accounts/verify-otp/', views.verify_login_otp, name='verify_login_otp'),
    path('accounts/confirm-email/', views.CustomConfirmEmailView.as_view(), name='account_confirm_email'),
    path('activity-log/', views.activity_log_view, name='activity_log'),
]