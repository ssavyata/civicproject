from django import forms
from .models import Issue, Feedback

class IssueReportForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['title', 'description', 'category', 'location', 'photo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide a detailed description of the issue'}),
            'title': forms.TextInput(attrs={'placeholder': 'e.g Large pothole near Mahendrapool'}),
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