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
]