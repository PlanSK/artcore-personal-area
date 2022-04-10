from django import template

from salary.models import *


register = template.Library()


@register.simple_tag()
def unverified_shift():
    return WorkingShift.objects.exclude(is_verified=True).count()


@register.simple_tag()
def inactive_user():
    return User.objects.exclude(is_active=True).filter(
        profile__dismiss_date=None
    ).count()


@register.inclusion_tag('salary/icon_logic.html')
def icon_logic(variable=None):
    return {'logic_trigger': variable}