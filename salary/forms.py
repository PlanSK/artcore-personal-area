from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

import datetime
import logging

from .models import *
from salary.services.registration import coming_of_age_date_string


logger = logging.getLogger(__name__)


class DateInput(forms.DateInput):
    input_type = 'date'


class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name',
                  'email', 'password1', 'password2']

    def clean_email(self):
        entered_email = self.cleaned_data['email']
        if not entered_email:
            raise forms.ValidationError("Email field cannot be empty")
        elif User.objects.filter(email=entered_email).exists():
            raise forms.ValidationError("This email already used")
        return entered_email


class DismissalEmployeeForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ('dismiss_date',)
        widgets = {
            'dismiss_date': DateInput(),
        }


class EmployeeRegistrationForm(forms.ModelForm):
    position = forms.ModelChoiceField(
        queryset=Position.objects.all().exclude(name='staff').exclude(
            name='trainee'),
        label='Должность', empty_label=None
    )

    class Meta:
        model = Profile
        fields = (
            'birth_date', 'employment_date',
            'position', 'photo',
        )

        widgets = {
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'max': coming_of_age_date_string(),
            }),
            'employment_date': forms.DateInput(attrs={
                'type': 'date',
                'max': datetime.date.today().strftime('%Y-%m-%d'),
            }),
        }


class StaffEditProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = [
            'birth_date', 'employment_date', 'position',
            'photo', 'dismiss_date', 'profile_status',
            'profile_comment'
        ]
        if settings.ATTESTATION_ENABLED:
            fields.append('attestation_date')
        widgets_injection = {
            field: forms.DateInput(attrs={'type': 'date',}, format='%Y-%m-%d')
            for field in fields if 'date' in field
        }
        widgets = dict()
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
        widgets = dict()
        widgets.update(widgets_injection)


class EmplModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        return obj.get_full_name()


class EditWorkshiftDataForm(forms.ModelForm):
    base_queryset = User.objects.filter(is_active=True)
    hall_admin_queryset = base_queryset.filter(profile__position__in=[1, 4])
    cashier_queryset = base_queryset.filter(profile__position__in=[2, 4])
    
    hall_admin = EmplModelChoiceField(
        queryset=hall_admin_queryset,
        label='Администратор зала',
    )
    cash_admin = EmplModelChoiceField(
        queryset=cashier_queryset,
        label='Администратор кассы',
    )
    next_hall_admin = EmplModelChoiceField(
        queryset=hall_admin_queryset,
        label='Прибывшая смена (Администратор)',
    )
    next_cashier = EmplModelChoiceField(
        queryset=cashier_queryset,
        label='Прибывшая смена (Кассир)',
    )

    class Meta:
        model = WorkingShift
        fields = [
            'hall_admin',
            'cash_admin',
            'bar_revenue',
            'game_zone_revenue',
            'additional_services_revenue',
            'hookah_revenue',
            'next_hall_admin',
            'next_cashier',
            'hall_admin_arrival_time',
            'cashier_arrival_time',
            'acquiring_evator_sum',
            'acquiring_terminal_sum',
            'cash_sum',
            'short_change_sum',
            'technical_report',
            'wishes',
        ]
        if settings.PUBLICATION_ENABLED:
            fields.append('publication_link')
        widgets = {
            'shift_date': forms.DateInput(attrs={'type': 'date'}),
            'hall_admin_arrival_time': forms.TimeInput(
                attrs={'type': 'time',}),
            'cashier_arrival_time': forms.TimeInput(
                attrs={'type': 'time',}),
        }


class AddWorkshiftDataForm(EditWorkshiftDataForm):
    technical_report = forms.BooleanField(label='Технический ответ в наличии',
                                          required=True)
    class Meta(EditWorkshiftDataForm.Meta):
        fields = ['shift_date']
        fields.extend(EditWorkshiftDataForm.Meta.fields)

    def clean(self):
        cleaned_data = super().clean()
        shift_date = cleaned_data.get('shift_date')
        today = datetime.date.today()
        logger.debug(f'[2/3] Today date value set {today}')
        if shift_date > datetime.date.today():
            logger.debug(
                f'[3/3] Current date value more than {today}. '
                f'I must raise exception.'
            )
            raise forms.ValidationError(
                f'The date must be no more than {today}'
            )
        else:
            logger.debug(
                f'[3/3] Successful validation in forms. Date: {shift_date}. '
                f'Today: {today}.'
            )
        return cleaned_data


class StaffEditWorkshiftForm(forms.ModelForm):
    base_queryset = User.objects.all()
    employee_queryset = base_queryset.filter(profile__position__in=[1, 2, 4])
    
    hall_admin = EmplModelChoiceField(
        queryset=employee_queryset,
        label='Администратор зала',
    )
    cash_admin = EmplModelChoiceField(
        queryset=employee_queryset,
        label='Администратор кассы',
    )
    next_hall_admin = EmplModelChoiceField(
        queryset=employee_queryset,
        label='Прибывшая смена (Администратор)',
    )
    next_cashier = EmplModelChoiceField(
        queryset=employee_queryset,
        label='Прибывшая смена (Кассир)',
    )

    class Meta:
        model = WorkingShift
        fields = [
            'hall_admin',
            'cash_admin',
            'bar_revenue',
            'game_zone_revenue',
            'additional_services_revenue',
            'hookah_revenue',
            'next_hall_admin',
            'next_cashier',
            'hall_admin_arrival_time',
            'cashier_arrival_time',
            'acquiring_evator_sum',
            'acquiring_terminal_sum',
            'cash_sum',
            'short_change_sum',
            'technical_report',
            'wishes',
            'shortage',
            'shortage_paid',
            'comment_for_cash_admin',
            'comment_for_hall_admin',
            'hall_cleaning',
            'status',
        ]
        if settings.PUBLICATION_ENABLED:
            fields.append('publication_link')
        widgets = {
            'shift_date': forms.DateInput(attrs={'type': 'date'}),
            'hall_admin_arrival_time': forms.TimeInput(
                attrs={'type': 'time',}),
            'cashier_arrival_time': forms.TimeInput(
                attrs={'type': 'time',}),
        }


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
                'value': datetime.date.today().strftime('%Y-%m-%d'),
            }),
            'workshift_date': forms.DateInput(attrs={
                'type': 'date',
                'value': datetime.date.today().strftime('%Y-%m-%d'),
            }),
        }   

class EditMisconductForm(forms.ModelForm):
    intruder = EmplModelChoiceField(
        queryset=User.objects.filter(is_staff=False),
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


class ErrorKNAForm(forms.ModelForm):
    class Meta:
        model = ErrorKNA
        fields = '__all__'
        widgets = {
            'error_time': forms.TimeInput(attrs={'type': 'time'}),
            'workshift': forms.HiddenInput(),
        }


class CostForm(forms.ModelForm):
    cost_person = EmplModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=False),
        label='Кто потратил',
    )

    class Meta:
        model = Cost
        fields = '__all__'
        widgets = {
            'workshift': forms.HiddenInput(),
        }


class CabinErrorForm(forms.ModelForm):
    class Meta:
        model = CabinError
        fields = '__all__'
        widgets = {
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'workshift': forms.HiddenInput(),
        }
