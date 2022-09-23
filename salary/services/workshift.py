import datetime

from django.contrib.auth.models import User
from django.conf import settings

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

def get_experience_bonus(employee, shift_date) -> float:
    current_experience = (shift_date - employee.profile.employment_date).days
    if settings.REQUIRED_EXPERIENCE <= current_experience:
        return settings.EXPERIENCE_BONUS

    return 0.0

def get_publication_bonus(self) -> float:
    if self.publication_link and self.publication_is_verified:
        return settings.PUBLICATION_BONUS

    return 0.0

def get_attestation_bonus(self, employee) -> float:
    if (employee.profile.attestation_date and
            employee.profile.attestation_date <= self.shift_date):
        return settings.ATTESTATION_BONUS

    return 0.0
