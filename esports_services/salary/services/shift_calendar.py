import calendar
import datetime
from typing import List
from collections import namedtuple

from django.contrib.auth.models import User
from django.db.models import QuerySet, Q

from salary.models import WorkingShift
from salary.services.google_sheets import get_employees_schedule_dict


CalendarDay = namedtuple(
    'CalendarDay',
    ['date', 'earnings', 'is_planed', 'link']
)
UserCalendar = namedtuple(
    'UserCalendar',
    ['weeks_list', 'complited_shifts_count',
     'planed_shifts_count', 'sum_of_earnings']
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
    """
    Returns a QuerySet with shifts in the specified month of the year.
    """

    return WorkingShift.objects.select_related(
            'hall_admin__profile__position',
            'cash_admin__profile__position'
        ).filter(
            shift_date__month=date.month,
            shift_date__year=date.year,
        ).filter(
            Q(cash_admin=user) | Q(hall_admin=user)
        ).order_by('shift_date')


def get_workshift_tuples_list(user: User, 
                              date: datetime.date) -> List[CalendarDay]:
    """
    Return list of CalendarDay namedtuple from workshifts data.
    """

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
                date=workshift.shift_date - datetime.timedelta(days=1),
                earnings=current_earnings,
                is_planed=False,
                link=workshift.get_absolute_url()
            )
        )
    return workshift_tuples_list


def get_calendar_weeks_list(
    weeks_days_list: List[List[int]],
    shift_dates_list: List[datetime.date],
    date: datetime.date,
    workshift_tuples_list: List[CalendarDay],
    planed_workshifts: List[int]
    ) -> List[List[CalendarDay]]:
    """
    Returns List[List[CalendarDay]] - list of lists with CalendarDay
    """

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

    return calendar_weeks_list


def get_user_calendar(user: User, date: datetime.date) -> UserCalendar:
    """
    Return UserCalendar namedtuple.
        weeks_list: List[List[CalendarDay]] - list of lists with CalendarDay
        complited_shifts_count: int - Closed shifts counter.
        all_shifts_count: int - All shifts counter.
        sum_of_earnings: float - Amount of earnings in closed shifts.
    """

    worksheet_name = 'Shift Schedule'

    planed_workshifts = get_employees_schedule_dict(
        worksheet_name
    ).get(user.get_full_name())

    workshift_tuples_list = get_workshift_tuples_list(user, date)

    complited_shifts_count: int = len(workshift_tuples_list)
    planed_shifts_count: int = 0
    
    if len(planed_workshifts) >= complited_shifts_count:
        planed_shifts_count = len(planed_workshifts) - complited_shifts_count

    sum_of_earnings = sum([shift.earnings for shift in workshift_tuples_list])
    shift_dates_list = [shift.date for shift in workshift_tuples_list]

    weeks_days_list = get_week_days_list(date.year, date.month)

    calendar_weeks_list = get_calendar_weeks_list(
        weeks_days_list,
        shift_dates_list,
        date,
        workshift_tuples_list,
        planed_workshifts
    )

    user_calendar = UserCalendar(
        weeks_list=calendar_weeks_list,
        complited_shifts_count=complited_shifts_count,
        planed_shifts_count=planed_shifts_count,
        sum_of_earnings=round(sum_of_earnings, 2)
    )

    return user_calendar
