from .captcha import generate_captcha_text, generate_captcha_image
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from accounts.models import User
from .models import Issue, Feedback, Department, IssuePhoto
from .decorators import citizen_required, officer_required
from .forms import IssueReportForm, FeedbackForm, IssueStatusForm, ProfileUpdateForm
from django.contrib import messages
from notifications.models import Notification
from .utils import assign_issue 
from django.core.paginator import Paginator
from django.db.models import Count, Q

# Create your views here.

#Citizen Views

@citizen_required
def citizen_dashboard(request):
    if not request.user.is_citizen():
        return redirect('login')

    all_issues = Issue.objects.filter(
        citizen=request.user
    ).order_by('-submitted_at')

    context = {
        'stats': {
            'total': all_issues.count(),
            'pending': all_issues.filter(status='submitted').count(),
            'in_progress': all_issues.filter(status='in_progress').count(),
            'resolved': all_issues.filter(status='resolved').count(),
        },
        'recent_issues': all_issues[:5],
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
 
        # ── Profile info form ────────────────────────────────────────────────
        if form_type == "profile":
            profile_form = ProfileUpdateForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("profile")
            else:
                messages.error(request, "Please fix the errors below.")
 
        # ── Password change form ─────────────────────────────────────────────
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
    captcha_text = generate_captcha_text()
    captcha_image = generate_captcha_image(captcha_text)

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
            issue.save()

            for photo in files:
                IssuePhoto.objects.create(issue=issue, image=photo)

            assign_issue(issue)
            messages.success(request, 'Issue reported successfully! We will look into it.')
            return redirect('my_issues')

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
    issues = Issue.objects.filter(citizen=request.user).order_by("-submitted_at")

    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()

    if status:
        issues = issues.filter(status=status)
    if category:
        issues = issues.filter(category=category)

    paginator = Paginator(issues, 8)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, 'citizen/myissues.html', {
        "issues": page_obj,
        "page_obj": page_obj,
        "category_choices": Issue.CATEGORY_CHOICES,
    })

@citizen_required
def issue_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id, citizen=request.user)
    return render(request, 'citizen/issue_detail.html', {'issue': issue})

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
    
    return render(request, 'officer/officer_dashboard.html', {'issues': issues})

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
    return render(request, 'officer/update_issue_status.html', {'form': form, 'issue': issue})

@login_required
@officer_required  # <-- Fixed: Added the missing '@' symbol here!
def officer_issue_queue(request):
    """
    Renders a searchable, filterable master list of issues 
    assigned specifically to the logged-in officer's department.
    """
    issue_list = Issue.objects.filter(department=request.user.department).order_by('-submitted_at')

    # Search Query Filter
    query = request.GET.get('q', '').strip()
    if query:
        if query.isdigit():
            issue_list = issue_list.filter(Q(id=query) | Q(title__icontains=query) | Q(description__icontains=query))
        else:
            issue_list = issue_list.filter(Q(title__icontains=query) | Q(description__icontains=query))

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
        'page_obj': page_obj,
    }
    # Fixed: Points explicitly inside your 'officer' folder structure
    return render(request, 'officer/officer_issue_queue.html', context)


@login_required
@officer_required
def officer_profile(request):
    """
    Handles updating basic officer profile fields along with a secure 
    password mutation form on the same page.
    """
    profile_form = ProfileUpdateForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile_form = ProfileUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile parameters have been updated successfully.")
                return redirect('officer_profile')
            else:
                messages.error(request, "Please correct the errors in your profile information.")

        elif action == 'change_password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Keeps the officer logged in
                messages.success(request, "Your password has been securely updated.")
                return redirect('officer_profile')
            else:
                messages.error(request, "Password validation failed. Please check the rules.")

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    # Fixed: Points explicitly inside your 'officer' folder structure
    return render(request, 'officer/officer_profile.html', context)

#Notifications Views

@login_required
def notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifs.update(is_read=True)
    return render(request, 'issues/notifications.html', {'notifications': notifs})  


def landing_page(request):
    total_issues = Issue.objects.count()
    resolved_issues = Issue.objects.filter(status='resolved').count()

    if total_issues > 0:
        resolution_rate = round((resolved_issues / total_issues) * 100)
    else:
        resolution_rate = 87  # default display value until data exists

    categories = [
        {'name': 'Road damage', 'icon': 'construction'},
        {'name': 'Water supply', 'icon': 'water_drop'},
        {'name': 'Street lighting', 'icon': 'lightbulb'},
        {'name': 'Public property', 'icon': 'park'},
        {'name': 'Other', 'icon': 'more_horiz'},
    ]

    return render(request, 'landing_page.html', {
        'total_issues': total_issues,
        'resolution_rate': resolution_rate,
        'categories': categories,
    })




# ── ADMIN VIEWS ─────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        return redirect('login')

    total = Issue.objects.count()
    pending = Issue.objects.filter(status='submitted').count()
    in_progress = Issue.objects.filter(status='in_progress').count()
    resolved = Issue.objects.filter(status='resolved').count()
    assigned = Issue.objects.filter(status='assigned').count()

    recent_issues = Issue.objects.order_by('-submitted_at')[:8]

    # Issues by category for bar chart
    categories = Issue.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')

    # Calculate max for percentage bars
    max_count = categories[0]['count'] if categories else 1

    context = {
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'assigned': assigned,
        'recent_issues': recent_issues,
        'categories': categories,
        'max_count': max_count,
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

    issue = get_object_or_404(Issue, id=issue_id)

    if request.method == 'POST':
        officer_id = request.POST.get('officer')
        remarks = request.POST.get('remarks', '')

        if officer_id:
            officer = get_object_or_404(User, id=officer_id, role='officer')
            issue.assigned_officer = officer
            issue.assigned_department = officer.department
            issue.status = 'assigned'
            if remarks:
                issue.officer_remarks = remarks
            issue.save()

            # Notify citizen
            Notification.objects.create(
                user=issue.citizen,
                issue=issue,
                message=f'Your issue "{issue.title}" has been assigned and is being processed.'
            )
            messages.success(request, f'Issue assigned to {officer.get_full_name()}.')

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

def refresh_captcha(request):
    from django.http import JsonResponse
    captcha_text = generate_captcha_text()
    request.session['captcha_text'] = captcha_text
    captcha_image = generate_captcha_image(captcha_text)
    return JsonResponse({'image': captcha_image})