from django import forms
from .models import Issue, Feedback
from django.contrib.auth.forms import PasswordChangeForm
from accounts.models import User

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class IssueReportForm(forms.ModelForm):
    # ✅ Add separate multi-photo field (not in Meta.fields since it's not a model field)
    images = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
    )

    class Meta:
        model = Issue
        fields = ['title', 'description', 'category', 'location']  # ✅ Removed 'photo'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide a detailed description of the issue'}),
            'title': forms.TextInput(attrs={'placeholder': 'e.g Large pothole near Mahendrapool'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g Newroad, Near Bus Park'}),
        }

    def clean_images(self):
        files = self.files.getlist('images')

        if len(files) > 5:
            raise forms.ValidationError("You can upload a maximum of 5 images.")

        for f in files:
            if f.size > 5 * 1024 * 1024:
                raise forms.ValidationError(f"{f.name} exceeds the 5MB size limit.")
            if f.content_type not in ['image/jpeg', 'image/png']:
                raise forms.ValidationError(f"{f.name} must be a JPG or PNG.")

        return files

class IssueStatusForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['status', 'officer_remarks']
        widgets = {
            'officer_remarks': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add any remarks or updates regarding the issue'}),
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your experience and any suggestions for improvement'}),
        }
 
 
class ProfileUpdateForm(forms.ModelForm):
    """Updates first_name, last_name, and an optional phone field."""
 
    # If your User model has a phone field, include it.
    # If not, remove 'phone' from fields and the phone field below.
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"type": "tel"}),
    )
 
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True