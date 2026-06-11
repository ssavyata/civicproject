from django.urls import path
from . import views

urlpatterns = [

    # Citizen
    path('citizen_dashboard/', views.citizen_dashboard, name='citizen_dashboard'),
    path('report/', views.report_issue, name='report_issue'),
    path('profile/', views.profile, name='profile'),
    path('my_issues/', views.my_issues, name='my_issues'),
    path('my_issues/<int:issue_id>/', views.issue_detail, name='issue_detail'),
    path('my_issues/<int:issue_id>/feedback/', views.submit_feedback, name='submit_feedback'),


    #Admin
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/issues/', views.admin_all_issues, name='admin_all_issues'),
    path('admin-panel/assign/<int:issue_id>/', views.admin_assign_issue, name='admin_assign_issue'),
    path('admin-panel/departments/', views.admin_manage_departments, name='admin_manage_departments'),
    path('admin-panel/users/', views.admin_manage_users, name='admin_manage_users'),

    # Officer (ADDED THIS SECTION)
    path('officer/dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('officer/issue/<int:issue_id>/update/', views.update_issue_status, name='update_issue_status'),
    path('officer/queue/', views.officer_issue_queue, name='officer_issue_queue'),
    path('officer/profile/', views.officer_profile, name='officer_profile'),
    path('officer/issues/<int:issue_id>/update/', views.officer_update_status, name='officer_update_status'),

    # CAPTCHA
    path('captcha/refresh/', views.refresh_captcha, name='refresh_captcha'),
]