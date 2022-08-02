import datetime

from django.contrib.auth.models import User

from .shift_calendar import get_planed_workshifts_list


def check_permission_to_close(user: User, date: datetime.date) -> bool:
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
