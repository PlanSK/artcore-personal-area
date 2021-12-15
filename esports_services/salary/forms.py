from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import *


class UserRegistration(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class EmployeeRegistration(forms.ModelForm):
    position = forms.ModelChoiceField(queryset=Position.objects.all(), label='Должность')

    class Meta:
        model = Profile
        fields = ['birth_date', 'employment_date', 'position']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'employment_date': forms.DateInput(attrs={'type': 'date'})
        }


class AddWorkshiftData(forms.ModelForm):
    
    class Meta:
        model = WorkingShift
        fields = '__all__'