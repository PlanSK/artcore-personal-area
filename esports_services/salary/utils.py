from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site

from unidecode import unidecode
from typing import *

from salary.models import Misconduct


class EmployeePermissionsMixin(PermissionRequiredMixin):
    permission_required = (
        'auth.add_user',
        'auth.change_user',
        'auth.view_user',
        'salary.add_profile',
        'salary.change_profile',
        'salary.view_profile',
    )


class WorkingshiftPermissonsMixin(PermissionRequiredMixin):
    permission_required = (
        'salary.view_workingshift',
        'salary.add_workingshift',
        'salary.change_workingshift',
        'salary.delete_workingshift',
        'salary.view_workshift_report',
        'salary.advanced_change_workshift',
    )


class MisconductPermissionsMixin(PermissionRequiredMixin):
    permission_required = (
        'salary.view_misconduct',
        'salary.add_misconduct',
        'salary.change_misconduct',
        'salary.delete_misconduct',
    )


class StaffOnlyMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        return self.request.user.is_staff


class TitleMixin(object):
    title = None

    def get_title(self):
        return self.title

    def get_context_data(self, **kwargs):
        context= super(TitleMixin, self).get_context_data(**kwargs)
        context['title'] = self.get_title()
        return context


class SuccessUrlMixin:
    success_url = reverse_lazy('index')

    def get_success_url(self):
        return self.request.GET.get('next', self.success_url)


class EditModelEditorFields:
    def form_valid(self, form):
        self.object.editor = self.request.user.get_full_name()
        self.object.change_date = timezone.localtime(timezone.now())
        return super().form_valid(form)


def return_misconduct_slug(last_name, date):
    slug_name = slugify(f'{unidecode(last_name)} {date.strftime("%d %m %Y")}')
    count = Misconduct.objects.filter(slug__startswith=slug_name).count()
    if not count:
        return slug_name
    else:
        return f'{slug_name}-{count}'


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

account_activation_token = TokenGenerator()


def get_confirmation_message(user, request=None):
    mail_template = 'salary/auth/confirmation_email.html'
    token_genertor = account_activation_token
    current_site = get_current_site(request)

    email_address = user.email
    mail_subject = 'Активация Вашей учетной записи.'
    message = render_to_string(mail_template, {
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'user': user,
        'token': token_genertor.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http',
    })
    return EmailMessage(mail_subject, message, to=[email_address])
