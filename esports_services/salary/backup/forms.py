from datetime import datetime
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms.models import ModelChoiceField

from .models import *


class UserRegistration(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class EmployeeRegistration(forms.ModelForm):
    position = forms.ModelChoiceField(
        queryset=Position.objects.all().exclude(position_salary=None), 
        label='Должность', empty_label=None
    )

    class Meta:
        model = Profile
        fields = ['birth_date', 'employment_date', 'position']
        widgets = {
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'max': '2003-01-01'
            }),
            'employment_date': forms.DateInput(attrs={'type': 'date'})
        }


class AddWorkshiftDataForm(forms.ModelForm):
    class EmplModelChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj) -> str:
            return ' '.join([obj.first_name, obj.last_name])

    hall_admin = EmplModelChoiceField(
        queryset=User.objects.filter(profile__position=1),
        label='Администратор зала'
    )
    cash_admin = EmplModelChoiceField(
        queryset=User.objects.filter(profile__position=2),
        label='Администратор кассы',
        disabled=True
    )
    class Meta:
        model = WorkingShift
        fields = [
            'hall_admin',
            'cash_admin',
            'shift_date',
            'bar_revenue',
            'game_zone_revenue',
            'vr_revenue'
        ]
        widgets = {
            'shift_date': forms.DateInput(attrs={
                'type': 'date',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'max': datetime.now().strftime('%Y-%m-%d'),
                'min': datetime.now().strftime('%Y-%m-%d'),
            }),
        }

class EditWorkshiftDataForm(forms.ModelForm):
    class EmplModelChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj) -> str:
            return ' '.join([obj.first_name, obj.last_name])

    hall_admin = EmplModelChoiceField(
        queryset=User.objects.filter(profile__position=1),
        label='Администратор зала'
    )
    cash_admin = EmplModelChoiceField(
        queryset=User.objects.filter(profile__position=2),
        label='Администратор кассы',
        disabled=True
    )
    class Meta:
        model = WorkingShift
        fields = [
            'hall_admin',
            'cash_admin',
            'bar_revenue',
            'game_zone_revenue',
            'vr_revenue'
        ]