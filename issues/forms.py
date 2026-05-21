from django import forms
from .models import Issue, Feedback
from accounts.models import User

class IssueReportForm(forms.ModelForm):

    class Meta:
        model = Issue
        fields = ['title', 'description', 'category', 'location']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g Large pothole near Mahendrapool'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide a detailed description of the issue'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g Newroad, Near Bus Park'}),
        }


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