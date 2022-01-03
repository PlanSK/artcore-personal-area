from django import template

from salary.models import *


register = template.Library()


@register.simple_tag()
def table_header(user):
    header = [
        'Дата', 'Бар', 'Game zone', 'Ошибки', 'Доп. услуги и VR', 'Общая выручка'
    ]
    cash_admin = [
        'Дисциплина',
        'Недостача',
        'Заработано',
        'Отметка о проверке',
        'Примечание'
    ]
    hall_admin = [
        'Дисциплина',
        'Поддержание чистоты',
        'Заработано',
        'Отметка о проверке'
    ]

    if user.profile.position.name == 'cash_admin':
        header.extend(cash_admin)
    elif user.profile.position.name == 'hall_admin':
        header.extend(hall_admin)

    return header
