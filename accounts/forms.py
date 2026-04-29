from django import forms
from .models import User
from django.contrib.auth.forms import UserCreationForm

class CitizenRegistrationForm(UserCreationForm):
    model = User
    fields = ['username', 'email', 'phone_number', 'ward_number', 'password1', 'password2']