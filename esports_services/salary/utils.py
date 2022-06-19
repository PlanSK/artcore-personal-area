from django.utils.text import slugify
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from unidecode import unidecode
from typing import *
from collections import namedtuple

from .config import *
from salary.models import *
import os
import logging


logger = logging.getLogger(__name__)


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


def get_user_media_dir_name(employee: User) -> str:
    """Return name of employee dirctory in MEDIA_ROOT

    Args:
        employee (User): Django User object
    """
    return f'user_{employee.id}'


def get_document_directory_path(employee: User) -> str:
    """Возвращает предполагаемый путь к папке с документами пользователя.
    """

    return os.path.join(
        get_user_media_dir_name(employee),
        DOCUMENTS_DIR_NAME,
    )


def get_employee_file_url(employee: User, filename: str) -> str:
    return '/'.join([
        get_user_media_dir_name(employee),
        DOCUMENTS_DIR_NAME,
        filename
    ])


def document_file_handler(employee: User, file: InMemoryUploadedFile) -> None:
    """Обработчик загружаемого файла для его сохранения в директории сотрудника.

    Args:
        employee (User): Объект модели сотрудника
        file (InMemoryUploadedFile): Объект загружаемого файла
    """

    document_directory_path = get_document_directory_path(employee)
    storage = FileSystemStorage()
    file_ext = os.path.splitext(file.name)[1]
    filename = storage.get_alternative_name(
        slugify(f'doc_{unidecode(employee.last_name)}'),
        file_ext
    )
    save_file_path = os.path.join(document_directory_path, filename)
    storage.save(save_file_path, file)


def get_employee_documents_urls(employee: User) -> Tuple[str]:
    """Возвращает список документов, находящихся в папке DOCUMENTS_DIR_NAME

    Args:
        employee (User): Объект модели сотрудника.
    """

    employee_document_dir_path = get_document_directory_path(employee)
    file_urls_tuple = tuple()
    file_storage = FileSystemStorage()
    if os.path.exists(os.path.join(
        file_storage.location,
        employee_document_dir_path
    )):
        if file_storage.listdir(employee_document_dir_path)[-1]:
            file_urls_tuple = (
                file_storage.url(get_employee_file_url(employee, name))
                for name in file_storage.listdir(employee_document_dir_path)[-1]
            )

    return file_urls_tuple


def delete_document_from_storage(employee: User, filename: str) -> None:
    """Delete document file from DOCUMENTS_DIR_NAME

    Args:
        employee (User): Django model User
        filename (str): Filename
    """
    file_path = os.path.join(get_document_directory_path(employee), filename)
    FileSystemStorage().delete(name=file_path)


class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name, max_length=None):
        """Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name


Intruder = namedtuple('Intruder', 'employee total_count explanation_count decision_count')
