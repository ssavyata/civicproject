from django.urls import path
from . import views

urlpatterns = [
    path('report/', views.report_issue, name='report_issue'),
    path('my-issues/', views.my_issues, name='my_issues'),
    path('issue/<int:issue_id>/', views.issue_detail, name='issue_detail'),
    path('issue/<int:issue_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('officer-dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('officer/update/<int:issue_id>/', views.update_issue_status, name='update_issue_status'),
]