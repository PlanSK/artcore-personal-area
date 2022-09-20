import os
from unidecode import unidecode

from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.text import slugify
from typing import Tuple


def get_user_media_dir_name(employee: User) -> str:
    """Return name of employee dirctory in MEDIA_ROOT

    Args:
        employee (User): Django User object
    """
    return f'user_{employee.id}'


def user_directory_path(instance, filename) -> str:
    file_extension = os.path.splitext(filename)[1]
    return os.path.join(
        get_user_media_dir_name(instance.user),
        os.path.normcase('photo' + file_extension)
    )


class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name, max_length=None):
        """Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name

def get_document_directory_path(employee: User) -> str:
    """Возвращает предполагаемый путь к папке с документами пользователя.
    """

    return os.path.join(
        get_user_media_dir_name(employee),
        settings.DOCUMENTS_DIR_NAME,
    )


def get_employee_file_url(employee: User, filename: str) -> str:
    return '/'.join([
        get_user_media_dir_name(employee),
        settings.DOCUMENTS_DIR_NAME,
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
