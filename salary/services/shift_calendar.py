import calendar
import datetime
import logging

from typing import List, NamedTuple

from django.db.models import QuerySet
from django.utils import timezone
from django.conf import settings

from salary.models import WorkingShift
from salary.services.google_sheets import get_employees_schedule_dict
from salary.services.db_orm_queries import (
    get_user_full_name_from_db, get_user_month_workshifts,
    has_cashier_permissions
)


class CalendarDay(NamedTuple):
    date: datetime.date
    earnings: float
    is_planed: bool
    is_verified: bool
    link: str


class UserCalendar(NamedTuple):
    weeks_list: list
    complited_shifts_count: int
    planed_shifts_count: int
    sum_of_earnings: float


class EmployeeOnWork(NamedTuple):
    cashier: str | None
    hall_admin: str | None


logger = logging.getLogger(__name__)


def get_week_days_list(year: int, month: int) -> List[List]:
    """
    Return a matrix representing a month's calendar.
    Each row represents a week; week entries are
    (day number, weekday number) tuples. Day numbers outside this month
    are zero.
    """
    calendar_instance = calendar.Calendar(firstweekday=0)
    try:
        month_calender = calendar_instance.monthdayscalendar(year=year,
                                                             month=month)
    except calendar.IllegalMonthError:
        logger.exception(f'Bad month number. {exception}')
        raise TypeError(
            'Error in arguments type monthdayscalendar(). Bad month number.')
    except TypeError as exception:
        logger.exception(
            f'Error in arguments type monthdayscalendar(): {exception}')
        raise

    return month_calender


def get_workshift_tuples_list(user_id: int,
                              year: int,
                              month: int) -> List[CalendarDay]:
    """
    Return list of CalendarDay namedtuple from workshifts data.
    """

    workshifts: QuerySet = get_user_month_workshifts(
        user_id=user_id,
        year=year,
        month=month
    )

    workshift_tuples_list = []
    for workshift in workshifts:
        if workshift.hall_admin.pk == user_id:
            earnings = workshift.hall_admin_earnings
        else:
            earnings = workshift.cashier_earnings
        current_earnings: float = earnings.final_earnings
        displayed_date = workshift.shift_date - datetime.timedelta(days=1)
        if workshift.shift_date == datetime.date(year, month, 1):
            displayed_date = workshift.shift_date
        is_verified = True if WorkingShift.WorkshiftStatus.VERIFIED else False
        workshift_tuples_list.append(
            CalendarDay(
                date=displayed_date,
                earnings=current_earnings,
                is_planed=False,
                is_verified=is_verified,
                link=workshift.get_absolute_url()
            )
        )
    return workshift_tuples_list


def get_calendar_weeks_list(
    weeks_days_list: List[List[int]],
    shift_dates_list: List[datetime.date],
    year: int, month: int,
    workshift_tuples_list: List[CalendarDay],
    planed_workshifts_list: List[datetime.date]
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
                date_of_day = datetime.date(year, month, day)
                if date_of_day in shift_dates_list:
                    day_tuple = [
                        day for day in workshift_tuples_list 
                        if day.date == date_of_day
                    ][0]
                elif date_of_day in planed_workshifts_list:
                    day_tuple = CalendarDay(
                        date=date_of_day,
                        earnings=None,
                        is_planed=True,
                        is_verified=False,
                        link=None
                    )
                else:
                    day_tuple = CalendarDay(
                        date=date_of_day,
                        earnings=None,
                        is_planed=False,
                        is_verified=False,
                        link=None
                    )
                day_tuples_list.append(day_tuple)
        calendar_weeks_list.append(day_tuples_list)

    return calendar_weeks_list


def get_planed_workshifts_days_list(user_id: int, month: int,
                                    year: int) -> list:
    """Returns list of day numbers planed shifts."""
    user_full_name = get_user_full_name_from_db(user_id)
    google_sheets_data_dict = get_employees_schedule_dict(year=year,
                                                          month=month)
    employee_days_list = google_sheets_data_dict.get(user_full_name, [])
    return employee_days_list


def get_user_calendar(user_id: int, year: int, month: int) -> UserCalendar:
    """
    Return UserCalendar namedtuple.
        weeks_list: List[List[CalendarDay]] - list of lists with CalendarDay
        complited_shifts_count: int - Closed shifts counter.
        all_shifts_count: int - All shifts counter.
        sum_of_earnings: float - Amount of earnings in closed shifts.
    """

    planed_workshifts_list = get_planed_workshifts_days_list(
        user_id=user_id,
        year=year,
        month=month
    )

    workshift_tuples_list = get_workshift_tuples_list(
        user_id=user_id,
        year=year,
        month=month
    )

    shift_dates_list: list = [shift.date for shift in workshift_tuples_list]

    weeks_days_list = get_week_days_list(year=year, month=month)

    calendar_weeks_list = get_calendar_weeks_list(
        weeks_days_list,
        shift_dates_list=shift_dates_list,
        year=year,
        month=month,
        workshift_tuples_list=workshift_tuples_list,
        planed_workshifts_list=planed_workshifts_list
    )

    complited_shifts_count: int = 0
    planed_shifts_count: int = 0
    sum_of_earnings: float = 0.0

    for week in calendar_weeks_list:
        for day in week:
            if day:
                if day.earnings:
                    complited_shifts_count += 1
                    if day.is_verified:
                        sum_of_earnings += day.earnings
                elif day.is_planed:
                    planed_shifts_count += 1

    if not planed_workshifts_list:
        planed_shifts_count = -1

    user_calendar = UserCalendar(
        weeks_list=calendar_weeks_list,
        complited_shifts_count=complited_shifts_count,
        planed_shifts_count=planed_shifts_count,
        sum_of_earnings=round(sum_of_earnings, 2)
    )

    return user_calendar


def get_employees_at_work() -> EmployeeOnWork:
    """Returns names of employees at work"""
    now = timezone.localtime(timezone.now())
    today = now.date()
    if now.hour < settings.EMPLOYEE_CHANGE_HOUR:
        today = now().date() - datetime.timedelta(days=1)
    current_month_employee_planed_shifts = get_employees_schedule_dict(
        year=today.year, month=today.month)
    employee_list = [
        name
        for name, dates in current_month_employee_planed_shifts.items()
        if today in dates
    ]

    try:
        hall_admin, cashier = employee_list
        if not has_cashier_permissions(cashier):
            hall_admin, cashier = cashier, hall_admin
    except ValueError:
        logger.warning('Number of employees at work not equal 2.')
        return EmployeeOnWork(None, None)
    else:
        return EmployeeOnWork(cashier=cashier, hall_admin=hall_admin)
