from django.db import models
from django.conf import settings


class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    email = models.EmailField()
    categories = models.JSONField(default=list)

    def __str__(self):
        return self.name


class Issue(models.Model):
    CATEGORY_CHOICES = [
        ('pothole', 'Pothole'),
        ('streetlight', 'Broken Streetlight'),
        ('water', 'Water Supply Issue'),
        ('waste', 'Waste/Garbage'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')

    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_issues'
    )

    assigned_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='issues'
    )

    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='handled_issues'
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    # ✅ Removed single 'photo' field — replaced by IssuePhoto below
    location = models.CharField(max_length=255)
    ward_number = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    officer_remarks = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    # ── Properties so templates can use issue.issue_id / .submitted_date / .reported_by ──

    @property
    def issue_id(self):
        return f"CR-{self.submitted_at.year}-{self.id:04d}"

    @property
    def submitted_date(self):
        return self.submitted_at

    @property
    def reported_by(self):
        return self.citizen

    # ── Photo helpers ────────────────────────────────────────────────────────────

    def primary_photo(self):
        return self.photos.first()

    def all_photos(self):
        return self.photos.all()


# ✅ New model — one row per uploaded photo
class IssuePhoto(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='issue_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for Issue #{self.issue.id} — {self.issue.title}"


class Feedback(models.Model):
    issue = models.OneToOneField(Issue, on_delete=models.CASCADE)
    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for Issue #{self.issue.id} by {self.citizen}"


class IssueStatusLog(models.Model):
    """Tracks every status change made by an officer on an issue."""
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='status_logs'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    status = models.CharField(max_length=30, choices=Issue.STATUS_CHOICES)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Issue #{self.issue.id} → {self.status} by {self.updated_by}"

    def get_status_display_label(self):
        return dict(Issue.STATUS_CHOICES).get(self.status, self.status)