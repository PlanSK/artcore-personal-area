import datetime

from django.contrib.auth.models import User
from django.conf import settings
from typing import NamedTuple, Union

from salary.services.shift_calendar import get_planed_workshifts_list


def check_permission_to_close(user: User, date: datetime.date) -> bool:
    """
    Check permissions and requesting days list from schedule and returning
    True if yesterday date in this list.
    """
    if user.has_perm('salary.add_workingshift'):
        yesterday = date - datetime.timedelta(days=1)
        planed_shifts = get_planed_workshifts_list(
            user=user,
            year=yesterday.year,
            month=yesterday.month
        )
        if yesterday.day in planed_shifts:
            return True

    return False


def notification_of_upcoming_shifts(user: User, date: datetime.date) -> bool:
    """
    Returning True if tomorrow in days list from schedule.
    """
    tomorrow = date + datetime.timedelta(days=1)
    planed_shifts = get_planed_workshifts_list(
            user=user,
            year=tomorrow.year,
            month=tomorrow.month
    )
    if tomorrow.day in planed_shifts:
        return True

    return False


# Earnings block moved from models.py
class WorkshiftData(NamedTuple):
    shift_date: datetime.date

class BasicPart(NamedTuple):
    salary: Union[float, None]
    experience: float
    attestation: float
    summary: float


def get_experience_bonus(employment_date: datetime.date,
                         shift_date: datetime.date) -> float:
    """
    Return REQUIRED_EXPERIENCE if experience more than 90 days or 0.0 if less
    """
    current_experience = (shift_date - employment_date).days
    if settings.REQUIRED_EXPERIENCE <= current_experience:
        return settings.EXPERIENCE_BONUS

    return 0.0


def get_attestation_bonus(attestation_date: datetime.date,
                          shift_date: datetime.date) -> float:
    """
    Return ATTESTATION_BONUS if attestation date is defined
    and older than shift date
    """
    if attestation_date and attestation_date <= shift_date:
        return settings.ATTESTATION_BONUS

    return 0.0


def get_basic_part(employee: User, workshift_date: datetime.date) -> BasicPart:
    """
    Return named tuple with basic part values: salary, experience, attestation
    and summry (sum of all values)
    """
    salary: Union[float, None] = employee.profile.position.salary,
    experience = 0.0
    attestation = 0.0
    summary = 0.0
    if salary:
        experience = get_experience_bonus(
            employee.profile.employment_date,
            workshift_date
        ),
        attestation = get_attestation_bonus(
            employee.profile.attestation_date,
            workshift_date
        )
        summary: float = sum((salary, experience, attestation))
    return BasicPart(
        salary=salary,
        experience=experience,
        attestation=attestation,
        summary=summary
    )
