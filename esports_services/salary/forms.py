from sqlite3 import Date
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

import datetime

from .models import *


class DateInput(forms.DateInput):
    input_type = 'date'


class UserRegistrationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class DismissalEmployeeForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ('dismiss_date',)
        widgets = {
            'dismiss_date': DateInput(),
        }


class EmployeeRegistrationForm(forms.ModelForm):
    position = forms.ModelChoiceField(
        queryset=Position.objects.all().exclude(name='staff'), 
        label='Должность', empty_label=None
    )

    class Meta:
        model = Profile
        fields = ['birth_date', 'employment_date', 'position', 'photo']
        widgets = {
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'max': '2003-01-01'
            }),
            'employment_date': forms.DateInput(attrs={'type': 'date'})
        }


class StaffEditProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ('birth_date', 'employment_date', 'position', 'photo', 'attestation_date', 'dismiss_date')
        widgets_injection = {
            field: forms.DateInput(attrs={'type': 'date',}, format='%Y-%m-%d')
            for field in fields if 'date' in field
        }
        widgets = {}
        widgets.update(widgets_injection)


class StaffEditUserForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active')


class EditUserForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class EditProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ('birth_date', 'employment_date', 'photo')
        widgets_injection = {
            field: forms.DateInput(attrs={'type': 'date',}, format='%Y-%m-%d')
            for field in fields if 'date' in field
        }
        widgets = {}
        widgets.update(widgets_injection)


class EmplModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        return obj.get_full_name()


class EditWorkshiftDataForm(forms.ModelForm):
    hall_admin = EmplModelChoiceField(
        queryset=User.objects.filter(is_active=True, profile__position=1),
        label='Администратор зала',
    )
    cash_admin = EmplModelChoiceField(
        queryset=User.objects.filter(is_active=True, profile__position=2),
        label='Администратор кассы',
    )

    class Meta:
        model = WorkingShift
        fields = [
            'hall_admin',
            'cash_admin',
            'bar_revenue',
            'game_zone_revenue',
            'game_zone_error',
            'vr_revenue',
            'hookah_revenue'
        ]


class AddWorkshiftDataForm(EditWorkshiftDataForm):

    class Meta:
        model = WorkingShift
        fields = [
            'hall_admin',
            'cash_admin',
            'shift_date',
            'bar_revenue',
            'game_zone_revenue',
            'game_zone_error',
            'vr_revenue',
            'hookah_revenue'
        ]
        widgets = {
            'shift_date': forms.DateInput(attrs={
                'type': 'date',
                'value': datetime.datetime.now().strftime('%Y-%m-%d'),
                'max': datetime.datetime.now().strftime('%Y-%m-%d'),
            }),
        }   


class StaffEditWorkshiftForm(EditWorkshiftDataForm):
    hall_admin = EmplModelChoiceField(
        queryset=User.objects.filter(profile__position=1),
        label='Администратор кассы',
    )
    cash_admin = EmplModelChoiceField(
        queryset=User.objects.filter(profile__position=2),
        label='Администратор кассы',
    )
    class Meta:
        model = WorkingShift
        fields = [
            'hall_admin',
            'cash_admin',
            'bar_revenue',
            'game_zone_revenue',
            'game_zone_error',
            'vr_revenue',
            'hookah_revenue',
            'hall_cleaning',
            'cash_admin_discipline',
            'cash_admin_discipline_penalty',
            'hall_admin_discipline',
            'hall_admin_discipline_penalty',
            'shortage',
            'shortage_paid',
            'comment',
            'is_verified'
        ]
