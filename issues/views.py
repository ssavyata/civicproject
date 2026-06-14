from accounts.models import User
from .captcha import generate_captcha_text, generate_captcha_image
from collections import Counter
from .duplicate_detector import find_duplicate_issue
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.conf import settings
from .decorators import citizen_required, officer_required
from .forms import IssueReportForm, FeedbackForm, IssueStatusForm, ProfileUpdateForm
from importlib.resources import files
import issues
from .models import Issue, Feedback, Department, IssuePhoto, IssueStatusLog
from notifications.models import Notification
from notifications.utils import notify
from .utils import assign_issue 
import json
import os
import requests
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib import messages

# Create your views here.

CATEGORY_ICONS = {
    'pothole':     'warning',
    'streetlight': 'light_mode',
    'water':       'water_drop',
    'waste':       'delete',
    'other':       'help_outline',
}

def landing_page(request):
    status_filter = request.GET.get('status', '')

    issues_qs = Issue.objects.filter(visibility='public').order_by('-submitted_at')
    if status_filter:
        issues_qs = issues_qs.filter(status=status_filter)

    status_counts = Issue.objects.aggregate(
        submitted=Count('id', filter=Q(status='submitted')),
        assigned=Count('id',   filter=Q(status='assigned')),
        in_progress=Count('id',filter=Q(status='in_progress')),
        resolved=Count('id',   filter=Q(status='resolved')),
        rejected=Count('id',   filter=Q(status='rejected')),
    )

    total = Issue.objects.count() or 1
    cat_qs = (
        Issue.objects
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    category_stats = [
        {
            'value':   row['category'],
            'label':   dict(Issue.CATEGORY_CHOICES).get(row['category'], row['category']),
            'icon':    CATEGORY_ICONS.get(row['category'], 'report'),
            'count':   row['count'],
            'percent': round(row['count'] / total * 100),
        }
        for row in cat_qs
    ]

    categories = [
        {'value': value, 'label': label, 'icon': CATEGORY_ICONS.get(value, 'report')}
        for value, label in Issue.CATEGORY_CHOICES
    ]

    resolved_count = status_counts['resolved']
    resolution_rate = round(resolved_count / total * 100) if total > 1 else 0

    context = {
        'public_issues':      issues_qs[:9],
        'submitted_count':    status_counts['submitted'],
        'assigned_count':     status_counts['assigned'],
        'in_progress_count':  status_counts['in_progress'],
        'resolved_count':     resolved_count,
        'rejected_count':     status_counts['rejected'],
        'category_stats':     category_stats,
        'categories':         categories,
        'status_filter':      status_filter,
        'total_issues':       Issue.objects.count(),
        'resolution_rate':    resolution_rate,
    }
    return render(request, 'landing_page.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def upload_issue_photo(request):
    try:
        photo = request.FILES.get('photo')
        if not photo:
            return JsonResponse({"success": False, "error": "No photo provided"}, status=400)

        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile

        filename = photo.name
        save_path = os.path.join(settings.MEDIA_PHOTOS_ROOT, filename)
        os.makedirs(settings.MEDIA_PHOTOS_ROOT, exist_ok=True)
        saved_path = default_storage.save(save_path, ContentFile(photo.read()))
        
        actual_filename = os.path.basename(saved_path)
        image_url = f"{settings.MEDIA_URL}{saved_path}"

        return JsonResponse({
            "success": True,
            "filename": actual_filename,
            "image_url": image_url
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def analyze_image(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    try:
        body = json.loads(request.body)
        filename = body.get('filename')
        
        import base64, os
        image_path = os.path.join(settings.MEDIA_PHOTOS_ROOT, filename)
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        response = requests.post('http://localhost:11434/api/generate', json={
            "model": "llava",
            "prompt": "Describe this civic issue briefly for a report.",
            "images": [image_b64],
            "stream": False
        }, timeout=60)
        
        result = response.json()
        return JsonResponse({'success': True, 'description': result['response']})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


#Citizen Views
@citizen_required
def citizen_dashboard(request):
    if not request.user.is_citizen():
        return redirect('login')

    all_issues = Issue.objects.filter(citizen=request.user).order_by('-submitted_at')
    total_issues   = all_issues.count()
    resolved_count = all_issues.filter(status='resolved').count()
    resolution_rate = round((resolved_count / total_issues) * 100) if total_issues > 0 else 0

    monthly_qs = (
        all_issues
        .annotate(month=TruncMonth('submitted_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    today = timezone.now()
    month_map = {entry['month'].strftime('%b %Y'): entry['count'] for entry in monthly_qs}
    monthly_activity = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=30 * i)
        label = d.strftime('%b %Y')
        monthly_activity.append({'month': label, 'count': month_map.get(label, 0)})
    cat_qs = (
    all_issues
    .values('category')
    .annotate(count=Count('id'))
    .order_by('-count')
    )
    category_stats = [
    {
        'label': dict(Issue.CATEGORY_CHOICES).get(row['category'], row['category']),
        'count': row['count'],
    }
    for row in cat_qs
    ]

    context = {
        'stats': {
            'total':       total_issues,
            'pending':     all_issues.filter(status='submitted').count(),
            'in_progress': all_issues.filter(status='in_progress').count(),
            'resolved':    resolved_count,

        },
        'recent_issues':    all_issues[:5],
        'resolution_rate':  resolution_rate,
        'monthly_activity': monthly_activity,
        'category_stats':   category_stats,
    }
    return render(request, 'citizen/citizen_dashboard.html', context)

@citizen_required
def profile(request):
    user = request.user
 
    # Initialise both forms with current user data
    profile_form = ProfileUpdateForm(instance=user)
    password_form = PasswordChangeForm(user=user)
 
    if request.method == "POST":
        form_type = request.POST.get("form_type")
 
        if form_type == "profile":
            profile_form = ProfileUpdateForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("profile")
            else:
                messages.error(request, "Please fix the errors below.")

        elif form_type == "password":
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Keep the user logged in after password change
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                return redirect("profile")
            else:
                messages.error(request, "Please fix the errors below.")
 
    return render(request, "citizen/profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })

@login_required
def report_issue(request):
    if request.method == 'POST':
        form = IssueReportForm(request.POST, request.FILES)
        files = request.FILES.getlist('images')

        user_answer = request.POST.get('captcha_answer', '').strip().lower()
        correct_answer = request.session.get('captcha_text', '').lower()

        if user_answer != correct_answer:
            captcha_text = generate_captcha_text()
            request.session['captcha_text'] = captcha_text
            captcha_image = generate_captcha_image(captcha_text)
            messages.error(request, 'Incorrect captcha. Please try again.')
            return render(request, 'citizen/report_issue.html', {
                'form': form,
                'captcha_image': captcha_image,
            })

        if form.is_valid():
            issue = form.save(commit=False)
            issue.citizen = request.user
            issue.ward_number = request.user.ward_number
            issue.visibility = request.POST.get('visibility', 'public')
            issue.save()

            for photo in files:
                IssuePhoto.objects.create(issue=issue, image=photo)

            duplicate = find_duplicate_issue(issue)

            if duplicate:
                issue.merged_into = duplicate
                issue.is_duplicate = True
                issue.status = 'duplicate'
                issue.save()
                notify(
                    issue.citizen,
                    'Issue Merged',
                    f'Your issue "{issue.title}" is similar to existing report #{duplicate.id}. '
                    f'It has been merged and will be resolved together.',
                    'general',
                    issue
                )
                issue_id = f"CR-{issue.submitted_at.year}-{issue.id:04d}"
                return render(request, 'citizen/report_success.html', {
                    'issue_id': issue_id,
                    'merged': True,
                    'merged_into': duplicate.id,
                })
            else:
                assign_issue(issue)
                notify(
                    request.user,
                    'Issue Submitted',
                    f'Your issue "{issue.title}" has been submitted successfully.',
                    'issue_submitted',
                    issue
                )
                for admin in User.objects.filter(role='admin'):
                    notify(
                        admin,
                        'New Issue Submitted',
                        f'A new issue "{issue.title}" was submitted by '
                        f'{request.user.get_full_name() or request.user.username}.',
                        'issue_submitted',
                        issue
                    )
                issue_id = f"CR-{issue.submitted_at.year}-{issue.id:04d}"
                return render(request, 'citizen/report_success.html', {'issue_id': issue_id})

    else:
        form = IssueReportForm()
        captcha_text = generate_captcha_text()
        request.session['captcha_text'] = captcha_text
        captcha_image = generate_captcha_image(captcha_text)

    return render(request, 'citizen/report_issue.html', {
        'form': form,
        'captcha_image': captcha_image,
    })

@citizen_required
def my_issues(request):
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()

    issues = Issue.objects.filter(citizen=request.user).order_by("-submitted_at")

    if status:
        issues = issues.filter(status=status)
    if category:
        issues = issues.filter(category=category)

    paginator = Paginator(issues, 8)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, 'citizen/myissues.html', {
        "issues": page_obj,
        "page_obj": page_obj,
        "status_filter": status,        
        "category_filter": category,   
        "category_choices": Issue.CATEGORY_CHOICES,
    })

@citizen_required
def issue_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id, citizen=request.user)
    return render(request, 'citizen/issue_detail.html', {'issue': issue})

@citizen_required
def submit_feedback(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id, citizen=request.user)

    if issue.status != 'resolved':
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

            # Notify admin that feedback was received
            for admin in User.objects.filter(role='admin'):
                notify(
                    admin,
                    'Feedback Received',
                    f'Citizen {request.user.get_full_name() or request.user.username} '
                    f'left feedback on resolved issue "{issue.title}".',
                    'general',
                    issue
                )

            # Notify the assigned officer about the feedback
            if issue.assigned_officer:
                notify(
                    issue.assigned_officer,
                    'Citizen Feedback Received',
                    f'Citizen {request.user.get_full_name() or request.user.username} '
                    f'rated your resolution of "{issue.title}" '
                    f'{feedback.rating}/5'
                    + (f': "{feedback.comment}"' if feedback.comment else '.'),
                    'general',
                    issue
                )

            messages.success(request, 'Thank you for your feedback!')
            return redirect('my_issues')
    else:
        form = FeedbackForm()

    return render(request, 'citizen/submit_feedback.html', {'form': form, 'issue': issue})


# Officer Views

@officer_required
def officer_dashboard(request):
    all_issues = Issue.objects.filter(
        assigned_department=request.user.department,
        assigned_officer=request.user
    ).order_by('-submitted_at')

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    issues_with_age = []
    for issue in all_issues[:10]:
        issue.days_old = (now - issue.submitted_at).days
        issues_with_age.append(issue)

    overdue_count = all_issues.filter(
        status='submitted',
        submitted_at__lt=seven_days_ago
    ).count()

    resolved_this_week = all_issues.filter(
        status='resolved',
        submitted_at__gte=seven_days_ago
    ).count()

    context = {
        'total_assigned':     all_issues.count(),
        'pending_count':      all_issues.filter(status='submitted').count(),
        'in_progress_count':  all_issues.filter(status='in_progress').count(),
        'resolved_count':     all_issues.filter(status='resolved').count(),
        'recent_issues':      issues_with_age,
        'overdue_count':      overdue_count,
        'resolved_this_week': resolved_this_week,
        'notifications':      Notification.objects.filter(
                                  user=request.user, is_read=False
                              ).order_by('-created_at')[:10],
    }
    return render(request, 'officer/officer_dashboard.html', context)

@officer_required
def update_issue_status(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    new_status = request.POST.get('status')
    issue.status = new_status
    issue.save()

    if new_status == 'resolved':
        notify(issue.citizen, 'Issue Resolved',
               f'Your issue "{issue.title}" has been resolved!',
               'issue_resolved', issue)
    elif new_status == 'rejected':
        notify(issue.citizen, 'Issue Rejected',
               f'Your issue "{issue.title}" was rejected.',
               'issue_rejected', issue)

    return redirect('admin_all_issues')

@login_required
@officer_required
def officer_issue_queue(request):
   
    issue_list = Issue.objects.filter(
        assigned_department=request.user.department,
        assigned_officer=request.user
    ).order_by('-submitted_at')

    query = request.GET.get('q', '').strip()
    if query:
        if query.isdigit():
            issue_list = issue_list.filter(
                Q(id=query) | Q(title__icontains=query) | Q(description__icontains=query)
            )
        else:
            issue_list = issue_list.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )

    # Dropdown Status and Category Filters
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        issue_list = issue_list.filter(status=status_filter)

    category_filter = request.GET.get('category', '').strip()
    if category_filter:
        issue_list = issue_list.filter(category=category_filter)

    # Pagination Setup (10 issues per page)
    paginator = Paginator(issue_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'issues':   page_obj,   
        'page_obj': page_obj,  
    }
    return render(request, 'officer/officer_issue_queue.html', context)


@login_required
@officer_required
def officer_profile(request):
   
    profile_form = ProfileUpdateForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')  

        if form_type == 'profile':
            profile_form = ProfileUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile has been updated successfully.")
                return redirect('officer_profile')
            else:
                messages.error(request, "Please correct the errors in your profile information.")

        elif form_type == 'password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  
                messages.success(request, "Your password has been securely updated.")
                return redirect('officer_profile')
            else:
                messages.error(request, "Password validation failed. Please check the rules.")

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }

    return render(request, 'officer/officer_profile.html', context)

@officer_required
def officer_update_status(request, issue_id):
    issue = get_object_or_404(
        Issue,
        id=issue_id,
        assigned_department=request.user.department,
        assigned_officer=request.user
    )

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        remarks    = request.POST.get('remarks', '').strip()

        if new_status:
            issue.status = new_status
            issue.assigned_officer = request.user
            if remarks:
                issue.officer_remarks = remarks
            issue.save()

            IssueStatusLog.objects.create(
                issue=issue,
                updated_by=request.user,
                status=new_status,
                remarks=remarks,
            )

            status_map = {
                'in_progress': ('status_changed', 'In Progress',
                    f'Your issue "{issue.title}" is now being worked on.'),
                'resolved':    ('issue_resolved', 'Issue Resolved',
                    f'Your issue "{issue.title}" has been resolved. Thank you for your patience!'),
                'rejected':    ('issue_rejected', 'Issue Rejected',
                    f'Your issue "{issue.title}" has been rejected.'
                    + (f' Reason: {remarks}' if remarks else '')),
            }

            notif_type, notif_title, notif_msg = status_map.get(
                new_status,
                ('status_changed', 'Issue Updated',
                 f'Your issue "{issue.title}" status changed to "{issue.get_status_display()}".')
            )

            # Sync ALL duplicate issues to the new status (not just resolved)
            for dup in issue.duplicates.all():
                dup.status = new_status
                dup.assigned_officer = issue.assigned_officer
                dup.officer_remarks = issue.officer_remarks
                dup.save()
                IssueStatusLog.objects.create(
                    issue=dup,
                    updated_by=request.user,
                    status=new_status,
                    remarks=remarks,
                )
                notify(dup.citizen, notif_title, notif_msg, notif_type, dup)

            # Notify the original issue's citizen
            notify(issue.citizen, notif_title, notif_msg, notif_type, issue)

            # Notify all admins
            for admin in User.objects.filter(role='admin'):
                notify(
                    admin,
                    f'Issue {issue.get_status_display()}',
                    f'Officer {request.user.get_full_name() or request.user.username} '
                    f'marked "{issue.title}" as {issue.get_status_display()}.',
                    notif_type,
                    issue
                )

            messages.success(request, 'Status updated and citizen notified.')
            return redirect('officer_issue_queue')

    context = {'issue': issue}
    return render(request, 'officer/officer_update_status.html', context)

#Admin Views

@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        return redirect('login')

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    total       = Issue.objects.count()
    pending     = Issue.objects.filter(status='submitted').count()
    in_progress = Issue.objects.filter(status='in_progress').count()
    resolved    = Issue.objects.filter(status='resolved').count()
    assigned    = Issue.objects.filter(status='assigned').count()
    rejected    = Issue.objects.filter(status='rejected').count()

    overdue_count = Issue.objects.filter(
        status='submitted',
        submitted_at__lt=seven_days_ago
    ).count()

    recent_issues_qs = Issue.objects.order_by('-submitted_at')[:8]
    recent_issues = []
    for issue in recent_issues_qs:
        issue.days_old  = (now - issue.submitted_at).days
        issue.is_overdue = (issue.status == 'submitted' and issue.days_old > 7)
        recent_issues.append(issue)

    # Issues by category
    categories = Issue.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    max_count = categories[0]['count'] if categories else 1

    # Monthly trend (last 6 months)
    monthly_qs = (
        Issue.objects
        .annotate(month=TruncMonth('submitted_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    month_map = {entry['month'].strftime('%b'): entry['count'] for entry in monthly_qs}
    monthly_trend = []
    for i in range(5, -1, -1):
        d = now - timedelta(days=30 * i)
        label = d.strftime('%b')
        monthly_trend.append({'month': label, 'count': month_map.get(label, 0)})

    context = {
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'assigned': assigned,
        'rejected': rejected,
        'overdue_count': overdue_count,
        'recent_issues': recent_issues,
        'categories': categories,
        'max_count': max_count,
        'monthly_trend': monthly_trend,
    }
    return render(request, 'admin/admin_dashboard.html', context)


@login_required
def admin_all_issues(request):
    if not request.user.is_admin():
        return redirect('login')

    issues = Issue.objects.all().order_by('-submitted_at')

    # Filters
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')

    if status_filter:
        issues = issues.filter(status=status_filter)
    if category_filter:
        issues = issues.filter(category=category_filter)

    departments = Department.objects.all()
    officers = User.objects.filter(role='officer')

    context = {
        'issues': issues,
        'departments': departments,
        'officers': officers,
        'status_filter': status_filter,
        'category_filter': category_filter,
    }
    return render(request, 'admin/all_issues.html', context)

@login_required
def admin_assign_issue(request, issue_id):
    if not request.user.is_admin():
        return redirect('login')

    issue = get_object_or_404(Issue, pk=issue_id)
    if request.method == 'POST':
        officer_id = request.POST.get('officer')
        remarks    = request.POST.get('remarks', '').strip()

        officer = get_object_or_404(User, pk=officer_id)
        issue.assigned_officer = officer
        issue.status = 'assigned'
        if remarks:
            issue.officer_remarks = remarks
        issue.save()

        # Notify the citizen
        notify(
            issue.citizen,
            'Issue Assigned',
            f'Your issue "{issue.title}" has been assigned to an officer and is being reviewed.',
            'issue_assigned',
            issue
        )

        # Notify the assigned officer
        notify(
            officer,
            'New Issue Assigned to You',
            f'Issue "{issue.title}" has been assigned to you.'
            + (f' Admin note: {remarks}' if remarks else ''),
            'issue_assigned',
            issue
        )

        messages.success(request, f'Issue assigned to {officer.get_full_name() or officer.username}.')
        return redirect('admin_all_issues')

    return redirect('admin_all_issues')


@login_required
def admin_manage_departments(request):
    if not request.user.is_admin():
        return redirect('login')

    departments = Department.objects.annotate(
        issue_count=Count('issues'),
        officer_count=Count('officers')
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            name = request.POST.get('name')
            email = request.POST.get('email')
            description = request.POST.get('description', '')
            categories = request.POST.getlist('categories')
            if name and email:
                Department.objects.create(
                    name=name,
                    email=email,
                    description=description,
                    categories=categories
                )
                messages.success(request, f'Department "{name}" created.')

        elif action == 'edit':
            dept_id = request.POST.get('dept_id')
            dept = get_object_or_404(Department, id=dept_id)
            dept.name = request.POST.get('name', dept.name)
            dept.email = request.POST.get('email', dept.email)
            dept.description = request.POST.get('description', dept.description)
            dept.categories = request.POST.getlist('categories')
            dept.save()
            messages.success(request, 'Department updated.')

        elif action == 'delete':
            dept_id = request.POST.get('dept_id')
            dept = get_object_or_404(Department, id=dept_id)
            dept.delete()
            messages.success(request, 'Department deleted.')

        return redirect('admin_manage_departments')

    return render(request, 'admin/manage_departments.html', {
        'departments': departments,
        'category_choices': Issue.CATEGORY_CHOICES,
        })


@login_required
def admin_manage_users(request):
    if not request.user.is_admin():
        return redirect('login')

    citizens = User.objects.filter(role='citizen').order_by('username')
    officers = User.objects.filter(role='officer').order_by('username')
    departments = Department.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_officer':
            username = request.POST.get('username')
            email = request.POST.get('email')
            dept_id = request.POST.get('department')
            password = request.POST.get('password')

            if username and email and dept_id and password:
                dept = get_object_or_404(Department, id=dept_id)
                officer = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role='officer',
                    ward_number=12,
                    department=dept
                )
                messages.success(request, f'Officer "{username}" created.')

        elif action == 'toggle_active':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User "{user.username}" {status}.')

        return redirect('admin_manage_users')

    context = {
        'citizens': citizens,
        'officers': officers,
        'departments': departments,
    }
    return render(request, 'admin/manage_users.html', context)

@login_required
def admin_issue_detail(request, pk):
    if not request.user.is_admin():
        return redirect('login')

    issue = get_object_or_404(Issue, pk=pk)
    feedback = getattr(issue, 'feedback', None)

    officers = User.objects.filter(
        role='officer',
        department=issue.assigned_department,
        is_active=True,
    )

    context = {
        'issue': issue,
        'feedback': feedback,
        'status_logs': issue.status_logs.all().order_by('created_at'),
        'photos': issue.photos.all(),
        'officers': officers,
    }
    return render(request, 'admin/issue_detail.html', context)

def refresh_captcha(request):
    from django.http import JsonResponse
    captcha_text = generate_captcha_text()
    request.session['captcha_text'] = captcha_text
    captcha_image = generate_captcha_image(captcha_text)
    return JsonResponse({'image': captcha_image})

User = get_user_model()

def password_reset_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            users = User.objects.filter(email__iexact=email, is_active=True)

            for user in users:
                uid   = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                reset_url = request.build_absolute_uri(
                    f'/password-reset/confirm/{uid}/{token}/'
                )

                # Render the HTML email template
                html_message = render_to_string('reset/reset_email.html', {
                    'user':     user,
                    'uid':      uid,
                    'token':    token,
                    'protocol': 'https' if request.is_secure() else 'http',
                    'domain':   request.get_host(),
                })

                send_mail(
                    subject='Reset your CivicReport password',
                    message=f'Reset your password here: {reset_url}',  # plain-text fallback
                    from_email=None,   # uses DEFAULT_FROM_EMAIL from settings
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()

    return render(request, 'reset/password_reset.html', {'form': form})

def password_reset_done_view(request):
    return render(request, 'reset/reset_done.html')

def password_reset_confirm_view(request, uidb64, token):
    validlink = False
    user      = None

    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True

        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset.')
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
    else:
        form = None

    return render(request, 'reset/reset_confirm.html', {
        'form':      form,
        'validlink': validlink,
    })

def password_reset_complete_view(request):
    return render(request, 'reset/reset_complete.html')