import datetime

from django import template
from django.contrib.auth.models import User
from django.db.models import Q
from salary.models import Message, Misconduct, Profile, WorkingShift

register = template.Library()


@register.simple_tag()
def unverified_shift():
    return WorkingShift.objects.exclude(is_verified=True).count()


@register.simple_tag()
def inactive_user():
    return Profile.objects.exclude(
        Q(profile_status='VD') | Q(profile_status='DSM')
    ).count()


@register.simple_tag()
def wait_explanation_misconducts():
    return Misconduct.objects.filter(status='AD').count()


@register.simple_tag()
def wait_decision_misconducts():
    return Misconduct.objects.filter(status='WT').count()


@register.simple_tag()
def today_workshift_exists_check():
    return WorkingShift.objects.filter(
        shift_date=datetime.date.today()).exists()


@register.simple_tag()
def get_verbose_status(status: str) -> str:
    return Profile.ProfileStatus(status).label


@register.simple_tag()
def get_unread_messages(user: User) -> int:
    return Message.objects.select_related('chat').filter(
        chat__members__in=[user],
        is_read=False
    ).exclude(author=user).count()