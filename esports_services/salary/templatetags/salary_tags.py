from django import template

from salary.models import *


register = template.Library()


@register.simple_tag()
def kpi_salary(workshift, user):
    return workshift.kpi_salary_calculate(user)

@register.simple_tag()
def return_key(dictonary: dict, name: str):
    return dictonary[name]


@register.simple_tag()
def get_year():
    return datetime.date.today().year


@register.simple_tag()
def unverified_shift():
    return WorkingShift.objects.exclude(is_verified=True).count()


@register.simple_tag()
def inactive_user():
    return User.objects.exclude(is_active=True).filter(
        profile__dismiss_date=None
    ).count()


@register.inclusion_tag('salary/cash_admin_workshifts.html')
def cash_admin_workshifts(user, workshifts, total_values):
    if not workshifts:
        current_month = datetime.date.today()
    else:
        current_month = workshifts[0].shift_date

    return {
        'user': user,
        'workshifts_list': workshifts,
        'total_values': total_values,
        'current_date': current_month
    }


@register.inclusion_tag('salary/hall_admin_workshifts.html')
def hall_admin_workshifts(user, workshifts, total_values):
    if not workshifts:
        current_month = datetime.date.today()
    else:
        current_month = workshifts[0].shift_date

    return {
        'user': user,
        'workshifts_list': workshifts,
        'total_values': total_values,
        'current_date': current_month
    }


@register.inclusion_tag('salary/icon_logic.html')
def icon_logic(variable=None):
    return {'logic_trigger': variable}