import calendar
import datetime
import logging

from dataclasses import dataclass
from enum import Enum
from typing import List, NamedTuple

from django.db.models import QuerySet
from django.utils import timezone
from django.conf import settings

from salary.models import WorkingShift
from salary.services.google_sheets import get_employees_schedule_dict
from salary.services.db_orm_queries import (
    get_user_full_name_from_db, get_user_month_workshifts,
    has_cashier_permissions, is_workshift_exists
)


class DayStatus(Enum):
    FOREIGN = 1
    REGULAR = 2
    PLANED = 3
    UNVERIFIED = 4
    VERIFIED = 5


@dataclass
class CalendarDay:
    date: datetime.date
    status: DayStatus = DayStatus.REGULAR
    earnings: float = 0.0
    url: str = ''


class Workshift(NamedTuple):
    shift_date: datetime.date
    earnings: float
    is_verified: bool
    url: str


class UserCalendar(NamedTuple):
    weeks_list: list
    complited_shifts_count: int
    planed_shifts_count: int
    sum_of_earnings: float


class EmployeeOnWork(NamedTuple):
    cashier: str | None
    hall_admin: str | None


logger = logging.getLogger(__name__)


def get_month_calendar(year: int, month: int) -> list[list[datetime.date]]:
    """
    Return a matrix representing a month's calendar.
    Each row represents a week; week entries are
    (day number, weekday number) tuples. Day numbers outside this month
    are zero.
    """
    calendar_instance = calendar.Calendar(firstweekday=0)
    month_calender = []
    try:
        month_calender = calendar_instance.monthdatescalendar(year=year,
                                                             month=month)
    except calendar.IllegalMonthError:
        logger.exception(
            'Error in arguments type monthdayscalendar(). Bad month number.')
    except TypeError as exception:
        logger.exception(
            f'Error in arguments type monthdayscalendar(): {exception}')

    return month_calender


def get_workshift_dict(user_id: int, year: int, month: int) -> dict:
    """Return list of CalendarDay namedtuple from workshifts data."""
    workshifts = get_user_month_workshifts(user_id=user_id, year=year,
                                           month=month)
    workshift_dict = dict()
    for workshift in workshifts:
        earnings = workshift.cashier_earnings
        is_verified = False
        if workshift.hall_admin.pk == user_id:
            earnings = workshift.hall_admin_earnings
        if workshift.status == WorkingShift.WorkshiftStatus.VERIFIED:
            is_verified = True
        workshift_url = workshift.get_absolute_url()
        current_workshift = Workshift(
            shift_date=workshift.shift_date,
            earnings=earnings.final_earnings,
            is_verified=is_verified,
            url=workshift_url
        )
        workshift_dict.update({
            workshift.shift_date: current_workshift
        })

    return workshift_dict


def get_planed_workshifts_days_list(user_id: int, month: int,
                                    year: int) -> list:
    """Returns list of day numbers planed shifts."""
    user_full_name = get_user_full_name_from_db(user_id)
    google_sheets_data_dict = get_employees_schedule_dict(year=year,
                                                          month=month)
    employee_days_list = google_sheets_data_dict.get(user_full_name, [])
    return employee_days_list


def is_planed_workshift_closed(required_date: datetime.date) -> bool:
    """Returns True if last day workshifts in month is closed"""
    required_date += datetime.timedelta(days=1)
    return is_workshift_exists(required_date)


def is_last_day_of_month(check_date: datetime.date) -> bool:
    """Return True if check date is last day oh moth"""
    next_day = check_date + datetime.timedelta(days=1)
    if next_day.month != check_date.month:
        return True

    return False


def is_workshift_on_last_day_planed(
        planed_workshifts_list: list[datetime.date]) -> bool:
    """Returns True if workshifts planed on last month day"""
    try:
        last_day_date_of_month = planed_workshifts_list[-1]
    except IndexError:
        return False

    return is_last_day_of_month(last_day_date_of_month)


def get_calendar_week_list(
        week: list[datetime.date], planed_workshifts_list: list[datetime.date],
        workshift_dict: dict, month: int) -> list:
    """Returns week list with CalendarDay's."""
    calendar_week_list = []
    for day_date in week:
        current_day = CalendarDay(day_date)
        tomorow = day_date + datetime.timedelta(days=1)
        if day_date.month != month:
            current_day.status = DayStatus.FOREIGN
        if (day_date in planed_workshifts_list 
                and tomorow not in workshift_dict.keys()):
            current_day.status = DayStatus.PLANED
        if (is_last_day_of_month(current_day.date)
                and is_planed_workshift_closed(current_day.date)):
            current_day.status = DayStatus.REGULAR
        if day_date in workshift_dict.keys():
            current_workshift: Workshift = workshift_dict.get(day_date)
            current_day.earnings = current_workshift.earnings
            current_day.status = DayStatus.UNVERIFIED
            if current_workshift.is_verified:
                current_day.status = DayStatus.VERIFIED
            current_day.url = current_workshift.url
        calendar_week_list.append(current_day)
    return calendar_week_list


def get_user_calendar(user_id: int, year: int, month: int) -> UserCalendar:
    """
    Return UserCalendar namedtuple.
        weeks_list: List[List[CalendarDay]] - list of lists with CalendarDay
        complited_shifts_count: int - Closed shifts counter.
        all_shifts_count: int - All shifts counter.
        sum_of_earnings: float - Amount of earnings in closed shifts.
    """

    planed_workshifts_list = get_planed_workshifts_days_list(
        user_id=user_id, year=year, month=month)
    workshift_dict = get_workshift_dict(user_id=user_id, year=year,
                                        month=month)
    month_calendar = get_month_calendar(year=year, month=month)
    calendar_days_month_list = []

    for week in month_calendar:
        calendar_week_list = get_calendar_week_list(
            week, planed_workshifts_list, workshift_dict, month)
        calendar_days_month_list.append(calendar_week_list)

    complited_shifts_count = len(workshift_dict.keys())
    planed_shifts_count = len(planed_workshifts_list)
    if is_workshift_on_last_day_planed(planed_workshifts_list):
        planed_shifts_count -= 1
    sum_of_earnings = sum([
        workshift.earnings
        for workshift in workshift_dict.values()
        if workshift.is_verified
    ])

    user_calendar = UserCalendar(
        weeks_list=calendar_days_month_list,
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
        today -= datetime.timedelta(days=1)
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
