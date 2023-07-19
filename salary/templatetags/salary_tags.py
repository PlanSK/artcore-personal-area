import datetime

from django import template
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone

from salary.models import Misconduct, Profile
from salary.services.profile_services import profile_photo_is_exists
from salary.services.chat import get_unread_messages_number
from salary.services.workshift import get_unclosed_workshift_number


register = template.Library()


@register.simple_tag()
def unverified_shift():
    return get_unclosed_workshift_number()


@register.simple_tag()
def inactive_user() -> int:
    return Profile.objects.exclude(
        Q(profile_status='VD') | Q(profile_status='DSM')
    ).count()


@register.simple_tag()
def wait_explanation_misconducts() -> int:
    return Misconduct.objects.filter(status='AD').count()


@register.simple_tag()
def wait_decision_misconducts() -> int:
    return Misconduct.objects.filter(status='WT').count()


@register.simple_tag()
def get_unread_messages(user: User) -> int:
    return get_unread_messages_number(user)


@register.simple_tag()
def check_image_file_exists(profile: Profile) -> bool:
    return profile_photo_is_exists(profile)
