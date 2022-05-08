from django import template
from django.db.models import Q

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


@register.simple_tag()
def unclosed_misconducts():
    return Misconduct.objects.filter(Q(status='AD') | Q(status='WT')).count()
