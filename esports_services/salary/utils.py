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
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings

from unidecode import unidecode
from typing import *
from collections import namedtuple

from .config import *
from salary.models import *
import os
import logging


logger = logging.getLogger(__name__)


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


def get_misconduct_slug(last_name, date):
    return slugify(f'{unidecode(last_name)} {date.strftime("%d %m %Y")}')


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


def get_choice_plural(amount: int, variants: tuple) -> str:
    """Возвращает слово во множественном числе, в зависимости от числа

    Args:
        amount (int): число
        variants (tuple): набор вариантов слов во множественном числе

    Returns:
        str: слово из набора во множественном числе
    """

    if amount % 10 == 1 and amount % 100 != 11:
        choice = 0
    elif amount % 10 >= 2 and amount % 10 <= 4 and \
            (amount % 100 < 10 or amount % 100 >= 20):
        choice = 1
    else:
        choice = 2

    return variants[choice]

def directory_make_if_not_exists(path: str) -> bool:
    """Проверяет существование пути, при его отсутствии пробует создать его.

    Args:
        path (str): путь для проверки

    Returns:
        bool: True если путь существует или успешно создан, в остальных случаях False.
    """

    directories_list = list()
    head_path = path

    while not os.path.exists(head_path):
        head_path, tail = os.path.split(head_path)
        directories_list.append(tail)
    
    for directory_name in directories_list:
        try:
            current_path = os.path.join(head_path, directory_name)
            os.mkdir(current_path)
        except OSError:
            logger.error(f'Unable to create target directory "{path}".')
            return False

    return True


def document_file_handler(employee: User, file: InMemoryUploadedFile) -> None:
    """Обработчик загружаемого файла для его сохранения в директории сотрудника.

    Args:
        employee (User): Объект модели сотрудника
        file (InMemoryUploadedFile): Объект загружаемого файла
    """
    document_directory_path = os.path.join(
        settings.MEDIA_ROOT,
        f'user_{employee.id}',
        DOCUMENTS_DIR_NAME,
    )

    if directory_make_if_not_exists(document_directory_path):
        with open(
            os.path.join(document_directory_path, os.path.normcase(file.name)),
            'wb+',
        ) as writable_file:
            for chunk in file.chunks():
                writable_file.write(chunk)


Intruder = namedtuple('Intruder', 'employee total_count explanation_count decision_count')
