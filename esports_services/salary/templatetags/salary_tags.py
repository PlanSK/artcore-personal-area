from django import template

from salary.models import *


register = template.Library()


@register.simple_tag()
def kpi_salary(workshift, user):
    return workshift.kpi_salary_calculate(user)


@register.inclusion_tag('salary/cash_admin_workshifts.html')
def cash_admin_workshifts(user, workshifts, total_values):
    return {
        'user': user,
        'workshifts_list': workshifts,
        'total_values': total_values
    }


@register.inclusion_tag('salary/hall_admin_workshifts.html')
def hall_admin_workshifts(user, workshifts, total_values):
    return {
        'user': user,
        'workshifts_list': workshifts,
        'total_values': total_values
    }


@register.inclusion_tag('salary/show_users.html')
def show_users():
    positions_list = dict()
    all_positions_list = Position.objects.exclude(name='staff')
    for get_position in all_positions_list:
        positions_list[get_position.title] = User.objects.filter(profile__position=get_position)

    return {'positions_list': positions_list}


@register.inclusion_tag('salary/staff_view_workshifts.html')
def staff_workshifts_view():
    workshifts_list = WorkingShift.objects.all().order_by('-shift_date')

    return {'workshifts_list': workshifts_list}


@register.inclusion_tag('salary/icon_logic.html')
def icon_logic(variable=None):
    return {'logic_trigger': variable}