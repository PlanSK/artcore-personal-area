import datetime

from django import template
from django.db.models import QuerySet
from django.contrib.auth.models import User
from django.db.models import Q
from salary.models import Message, Misconduct, Profile, WorkingShift
from salary.services.profile_services import profile_photo_is_exists

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

@register.simple_tag()
def get_birthday_person_list() -> QuerySet:
    today = datetime.date.today()
    birthday_person_list = User.objects.select_related('profile').filter(
        profile__birth_date__day=today.day,
        profile__birth_date__month=today.month,
    ).exclude(profile__profile_status='DSM')
    
    return birthday_person_list

@register.simple_tag()
def check_image_file_exists(profile: Profile):
    return profile_photo_is_exists(profile)
