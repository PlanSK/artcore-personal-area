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


@register.inclusion_tag('salary/show_users.html')
def show_users():
    positions_list = dict()
    all_positions_list = Position.objects.exclude(name='staff')
    for get_position in all_positions_list:
        positions_list[get_position.title] = User.objects.filter(profile__position=get_position)

    return {'positions_list': positions_list}
