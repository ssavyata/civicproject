from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Issue, Feedback
from .decorators import citizen_required, officer_required
from .forms import IssueReportForm, FeedbackForm, IssueStatusForm
from django.contrib import messages
from notifications.models import Notification
from .utils import assign_issue 

# Create your views here.

#Citizen Views

@citizen_required
def report_issue(request):
    if request.method == 'POST':
        form = IssueReportForm(request.POST, request.FILES)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.citizen = request.user.ward_number
            issue.save()
            assign_issue(issue)
            messages.success(request, 'Issue reported successfully! We will look into it.')
            return redirect('my_issues')
    else:
        form = IssueReportForm()
    return render(request, 'issues/submit_issue.html', {'form': form})

@citizen_required
def my_issues(request):
    issues = Issue.objects.filter(citizen=request.user).order_by('-submitted_at')
    return render(request, 'issues/my_issues.html', {'issues': issues})

@citizen_required
def issue_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id, citizen=request.user)
    return render(request, 'issues/issue_detail.html', {'issue': issue})

@citizen_required
def submit_feedback(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id, citizen=request.user)

    if issue.status != 'Resolved':
        messages.error(request, 'You can only give feedback on resolved issues.')
        return redirect('my_issues')
    
    if hasattr(issue, 'feedback'):
        messages.error(request, 'You have already submitted feedback for this issue.')
        return redirect('my_issues')
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.issue = issue
            feedback.citizen = request.user
            feedback.save()
            messages.success(request, 'Thank you for your feedback!')
            return redirect('my_issues')
    else:
        form = FeedbackForm()
    return render(request, 'issues/submit_feedback.html', {'form': form, 'issue': issue})


# Officer Views

@officer_required
def officer_dashboard(request):
    issues = Issue.objects.filter(
        assigned_department=request.user.department
        ).order_by('-submitted_at')
   
    status_filter = request.GET.get('status')
    if status_filter:
        issues = issues.filter(status=status_filter)
    
    return render(request, 'issues/officer_dashboard.html', {'issues': issues})

@officer_required
def update_issue_status(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id, assigned_department=request.user.department)

    if request.method == 'POST':
        form = IssueStatusForm(request.POST, instance=issue)
        if form.is_valid():
            form.save()

            # Create notification for the citizen
            Notification.objects.create(
                user = issue.citizen,
                issue = issue,
                message=f'Your issue "{issue.title}" has been updated to: {issue.get_status_display()}. {issue.officer_remarks}'
            )
            messages.success(request, 'Issue status updated and citizen notified!')
            return redirect('officer_dashboard')
    else:
        form = IssueStatusForm(instance=issue)
    return render(request, 'issues/update_issue_status.html', {'form': form, 'issue': issue})

#Notifications Views

@login_required
def notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifs.update(is_read=True)
    return render(request, 'issues/notifications.html', {'notifications': notifs})  