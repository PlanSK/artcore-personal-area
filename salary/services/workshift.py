import calendar
import datetime

from django.contrib.auth.models import User
from django.db.models import QuerySet

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


def get_missed_dates_list(
        dates_list: QuerySet[datetime.date]) -> list[datetime.date]:
    today = datetime.date.today()
    missed_dates_list = []
    max_day = today.day
    if dates_list:
        date_from_checked_dates = dates_list.last()
        if (date_from_checked_dates.month != today.month
                or date_from_checked_dates.year != today.year):
            max_day = calendar.monthrange(date_from_checked_dates.year,
                                          date_from_checked_dates.month)[1]

        days_range = range(1, max_day + 1)
        for day in days_range:
                current_date = datetime.date(
                    date_from_checked_dates.year,
                    date_from_checked_dates.month,
                    day
                )
                if not current_date in dates_list:
                    missed_dates_list.append(current_date)

    return missed_dates_list
