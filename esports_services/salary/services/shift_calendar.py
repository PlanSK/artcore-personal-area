import calendar
import datetime
from typing import List
from collections import namedtuple

from django.contrib.auth.models import User
from django.db.models import QuerySet, Q

from salary.models import WorkingShift
from .utils import time_of_run


CalendarDay = namedtuple('CalendarDay', ['date', 'earnings', 'is_planed'])


def get_week_days_list(year: int = None, month: int = None) -> List[List]:
    """
    Return a matrix representing a month's calendar.
    Each row represents a week; week entries are
    (day number, weekday number) tuples. Day numbers outside this month
    are zero. If year or month is not defined, use date.today() values.
    """
    if not year:
        year = datetime.date.today().year
    if not month:
        month = datetime.date.today().month

    try:
        datetime.date(year, month, 1)
    except (ValueError, TypeError):
        raise ValueError('Invalid year or month paramethers')

    calender_instance = calendar.Calendar(firstweekday=0)
    month_calender: list = calender_instance.monthdayscalendar(
        year=year,
        month=month,
    )
    return month_calender


def get_user_month_workshifts(user: User, date: datetime.date) -> QuerySet:
    return WorkingShift.objects.select_related(
            'hall_admin__profile__position',
            'cash_admin__profile__position'
        ).filter(
            shift_date__month=date.month,
            shift_date__year=date.year,
        ).filter(
            Q(cash_admin=user) | Q(hall_admin=user)
        ).order_by('shift_date')


@time_of_run
def get_user_calendar(user: User,
                        date: datetime.date) -> List[List[CalendarDay]]:
    """
    Return list of lists of namedtuples with days of month.
    """
    # Pass of google sheets shift dates
    import random
    planed_workshifts = [random.randrange(1, 30) for _ in range(1, 5)]

    workshifts = get_user_month_workshifts(user, date)
    shift_dates_list = workshifts.dates('shift_date', 'day')
    weeks_list = get_week_days_list(date.year, date.month)
    user_calendar = []
    for week in weeks_list:
        week_tuples_list = []
        for day in week:
            if day == 0:
                week_tuples_list.append(None)
            else:
                date_of_day = datetime.date(date.year, date.month, day)
                if date_of_day in shift_dates_list:
                    workshift = workshifts.get(shift_date=date_of_day)
                    earnings = {}
                    if workshift.hall_admin == user:
                        earnings = workshift.hall_admin_earnings_calc()
                    else:
                        earnings = workshift.cashier_earnings_calc()
                        
                    day_tuple = CalendarDay(
                        date=date_of_day,
                        earnings=earnings.get('final_earnings'),
                        is_planed = False
                    )
                elif date_of_day.day in planed_workshifts:
                    day_tuple = CalendarDay(
                        date=date_of_day,
                        earnings=None,
                        is_planed=True
                    )
                else:
                    day_tuple = CalendarDay(
                        date=date_of_day,
                        earnings=None,
                        is_planed=False
                    )
                week_tuples_list.append(day_tuple)
        user_calendar.append(week_tuples_list)
    return user_calendar
