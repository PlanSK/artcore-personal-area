import calendar
import datetime
from typing import List
from collections import namedtuple

from django.contrib.auth.models import User
from django.db.models import QuerySet, Q

from salary.models import WorkingShift


CalendarDay = namedtuple(
    'CalendarDay',
    ['date', 'earnings', 'is_planed', 'link']
)
UserCalendar = namedtuple(
    'UserCalendar',
    ['weeks_list', 'complited_shifts_count',
     'all_shifts_count', 'sum_of_earnings']
)

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


def get_user_calendar(user: User, date: datetime.date) -> UserCalendar:
    """
    Return UserCalendar namedtuple.
        weeks_list: List[List[CalendarDay]] - list of lists with namedtuples CalendarDay
        complited_shifts_count: int - Closed shifts counter.
        all_shifts_count: int - All shifts counter.
        sum_of_earnings: float - Amount of earnings in closed shifts.
    """
    # Pass of google sheets shift dates
    import random
    planed_workshifts = [random.randrange(1, 30) for _ in range(1, 5)]

    workshifts: QuerySet = get_user_month_workshifts(user, date)
    
    workshift_tuples_list = []
    sum_of_earnings: float = 0.0
    for workshift in workshifts:
        if workshift.hall_admin == user:
            earnings = workshift.hall_admin_earnings_calc()
        else:
            earnings = workshift.cashier_earnings_calc()
        current_earnings = earnings.get('final_earnings')
        sum_of_earnings += current_earnings
        workshift_tuples_list.append(
            CalendarDay(
                date=workshift.shift_date,
                earnings=current_earnings,
                is_planed=False,
                link=workshift.get_absolute_url()
            )
        )
    complited_shifts_count = len(workshift_tuples_list)
    all_shifts_count = complited_shifts_count + len(planed_workshifts)
    
    shift_dates_list = workshifts.dates('shift_date', 'day')

    weeks_days_list = get_week_days_list(date.year, date.month)
    calendar_weeks_list = []
    for week in weeks_days_list:
        day_tuples_list = []
        for day in week:
            if day == 0:
                day_tuples_list.append(None)
            else:
                date_of_day = datetime.date(date.year, date.month, day)
                if date_of_day in shift_dates_list:
                    day_tuple = [
                        day for day in workshift_tuples_list 
                        if day.date == date_of_day
                    ][0]
                elif date_of_day.day in planed_workshifts:
                    day_tuple = CalendarDay(
                        date=date_of_day,
                        earnings=None,
                        is_planed=True,
                        link=None
                    )
                else:
                    day_tuple = CalendarDay(
                        date=date_of_day,
                        earnings=None,
                        is_planed=False,
                        link=None
                    )
                day_tuples_list.append(day_tuple)
        calendar_weeks_list.append(day_tuples_list)
    user_calendar = UserCalendar(
        weeks_list=calendar_weeks_list,
        complited_shifts_count=complited_shifts_count,
        all_shifts_count=all_shifts_count,
        sum_of_earnings=round(sum_of_earnings, 2)
    )
    return user_calendar
