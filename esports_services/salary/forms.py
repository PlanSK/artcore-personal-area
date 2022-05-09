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

    def clean_email(self):
        entered_email = self.cleaned_data['email']
        if not entered_email:
            raise forms.ValidationError("Email field cannot be empty")
        elif User.objects.filter(email=entered_email).exists():
            raise forms.ValidationError("This email already used")
        return entered_email


class UserChoicesForm(forms.Form):
    users_list = list()
    for user in User.objects.select_related('profile').filter(is_active=True):
        mail_confirm_status = "+" if user.profile.email_is_confirmed else "-"
        users_list.append(
            ((user), f'[{mail_confirm_status}] {user.get_full_name()}')
        )

    users = forms.MultipleChoiceField(
        choices=users_list,
        label='Список пользователей',
        required=True,
        widget=forms.widgets.SelectMultiple(attrs={'size': 20})
    )


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
        fields = (
            'hall_admin',
            'cash_admin',
            'bar_revenue',
            'game_zone_revenue',
            'game_zone_error',
            'vr_revenue',
            'hookah_revenue',
            'publication_link',
        )


class AddWorkshiftDataForm(EditWorkshiftDataForm):

    class Meta:
        model = WorkingShift
        fields = (
            'hall_admin',
            'cash_admin',
            'shift_date',
            'bar_revenue',
            'game_zone_revenue',
            'game_zone_error',
            'vr_revenue',
            'hookah_revenue',
            'publication_link',
        )
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
        fields = (
            'hall_admin',
            'cash_admin',
            'bar_revenue',
            'game_zone_revenue',
            'game_zone_error',
            'vr_revenue',
            'hookah_revenue',
            'publication_is_verified',
            'publication_link',
            'hall_cleaning',
            'shortage',
            'shortage_paid',
            'comment_for_cash_admin',
            'comment_for_hall_admin',
            'is_verified',
        )


class AddMisconductForm(forms.ModelForm):
    intruder = EmplModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=False),
        label='Сотрудник',
    )

    class Meta:
        model = Misconduct
        fields = (
            'misconduct_date',
            'workshift_date',
            'intruder',
            'regulations_article',
            'penalty',
            'explanation_exist',
            'comment',
            'status',
        )
        widgets = {
            'misconduct_date': forms.DateInput(attrs={
                'type': 'date',
                'value': datetime.datetime.now().strftime('%Y-%m-%d'),
            }),
            'workshift_date': forms.DateInput(attrs={
                'type': 'date',
                'value': datetime.datetime.now().strftime('%Y-%m-%d'),
            }),
        }   

class EditMisconductForm(forms.ModelForm):
    intruder = EmplModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=False),
        label='Сотрудник',
        disabled = True,
    )

    class Meta:
        model = Misconduct
        fields = (
            'misconduct_date',
            'workshift_date',
            'intruder',
            'regulations_article',
            'penalty',
            'explanation_exist',
            'comment',
            'status',
        )
