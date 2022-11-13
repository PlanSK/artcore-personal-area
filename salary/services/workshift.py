import calendar
import datetime
import logging

from typing import NamedTuple

from django.contrib.auth.models import User
from django.db.models import QuerySet, Q, Sum
from django.utils import timezone

from salary.services.shift_calendar import get_planed_workshifts_days_list
from salary.services.monthly_reports import Rating, get_rating_data
from salary.models import WorkingShift


logger = logging.getLogger(__name__)


class EmployeeMonthIndicators(NamedTuple):
    summary_earnings: float
    summary_shortage: float
    number_of_verified_workshifts: int
    number_of_total_workshifts: int
    rating_data: Rating | None


def _is_date_day_exists_in_plan(full_name: str,
                           check_date: datetime.datetime) -> bool:
    """
    Returns True if day from check_date exists in the plan else returns False.
    """
    planed_shifts_days_tuple = get_planed_workshifts_days_list(
        user_full_name=full_name, month=check_date.month, year=check_date.year)
    logger.debug(f'Planed days: {planed_shifts_days_tuple}.')
    if check_date.day in planed_shifts_days_tuple:
        logger.debug(f'{check_date.day} exists in {planed_shifts_days_tuple}.')
        return True

    logger.debug(f'{check_date.day} is not exists in the plan.')
    return False


def _get_date_with_offset(
        offset: int,
        current_date: datetime.datetime| None = None) -> datetime.datetime:
    """
    Returns data with offset
    """
    if not current_date:
        date = timezone.now()
        logger.debug(f'Set default value of current_date: {date}.')
    else:
        date = current_date

    if offset > 0:
        return date + datetime.timedelta(offset)
    elif offset < 0:
        return date - datetime.timedelta(abs(offset))
    else:
        return date


def check_permission_to_close(
        user: User, date_to_close: datetime.datetime | None = None) -> bool:
    """
    Check permissions and requesting days list from schedule and returning
    True if yesterday date in this list.
    """
    global_permission = user.has_perm('salary.add_workingshift')
    yesterday = _get_date_with_offset(-1, date_to_close)
    logger.info(
        f'Start checking for permissions. User: {user.username}. '
        f'Global permission: {global_permission}. Yesterday value: {yesterday}'
    )

    if global_permission:
        is_planed = _is_date_day_exists_in_plan(user.get_full_name(),
                                                yesterday)
        if is_planed:
            logger.info(
                f'User {user.username} has permissions to close workshift.')
            return True

    logger.info(
        f'User {user.username} has no permissions to close workshift.')
    return False


def notification_of_upcoming_shifts(
        user: User, date_before: datetime.datetime | None = None) -> bool:
    """
    Returning True if tomorrow in days list from schedule.
    """
    tomorrow = _get_date_with_offset(1, date_before)
    logger.info(
        f'Start checking for permissions to show notification. '
        f'User: {user.username}. Tomorrow value: {tomorrow}.'
    )

    if _is_date_day_exists_in_plan(user.get_full_name(), tomorrow):
        logger.info(f'User {user.username} can see notification.')
        return True

    logger.info(f'Notification for user {user.username} do not show.')
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


def get_missed_dates(month: int, year: int,
                      full_name: str) -> tuple[datetime.date]:
    """
    Return tuple with missed dates of unclosed workshifts.
    """
    today_date = timezone.localdate(timezone.now())
    planed_days_numbers = get_planed_workshifts_days_list(
        full_name, month, year)
    exists_workshifts_dates = WorkingShift.objects.filter(
        shift_date__month=month, shift_date__year=year,
        shift_date__day__lte=today_date.day).dates('shift_date', 'day')

    month_dates = [
        datetime.date(year, month, day) for day in range(1, today_date.day + 1)
    ]
    missed_dates = [
        date for date in month_dates
        if date not in exists_workshifts_dates
    ]
    planed_shift_closed_dates = [
        _get_date_with_offset(1, datetime.date(year, month, day))
        for day in planed_days_numbers
    ]
    employee_missed_dates = [
        date for date in missed_dates
        if date in planed_shift_closed_dates
    ]
    first_month_day = datetime.date(year, month, 1)
    if today_date.day == first_month_day or first_month_day in missed_dates:
        yesterday = _get_date_with_offset(-1, first_month_day)
        last_month_planed_days = get_planed_workshifts_days_list(
        full_name, yesterday.month, yesterday.year)
        last_month_shift_date = datetime.date(
            yesterday.year, yesterday.month, last_month_planed_days[-1])
        if (not WorkingShift.objects.filter(shift_date=yesterday).exists()
                and last_month_shift_date == yesterday):
            employee_missed_dates.append(today_date)

    return tuple(employee_missed_dates)


def get_employee_month_workshifts(employee_id: int, month: int, year: int,
                                   only_verified: bool = False) -> QuerySet:
    """
    Returns Queryset with workshifts which has employee_id
    for the month of year.
    """
    employee_month_workshifts = WorkingShift.objects.select_related(
        'hall_admin__profile__position',
        'cash_admin__profile__position').filter(
            shift_date__month=month, shift_date__year=year).filter(
                Q(cash_admin__id=employee_id) | Q(hall_admin__id=employee_id)
            ).order_by('shift_date')

    if only_verified:
        return employee_month_workshifts.filter(is_verified=True)

    return employee_month_workshifts


def _get_summary_earnings(employee_id: int, month: int, year: int,
                          rating_data: Rating | None) -> float:
    """
    Reutrns summary earnings for the month.
    """
    employee_month_workshifts = get_employee_month_workshifts(
        employee_id, month, year, only_verified=True)
    summary_earnings = sum([
        workshift.hall_admin_earnings.final_earnings
        if workshift.hall_admin.id == employee_id
        else workshift.cashier_earnings.final_earnings
        for workshift in employee_month_workshifts
    ])
    if rating_data:
        summary_earnings += rating_data.bonus

    return round(summary_earnings, 2)


def get_employee_workshift_indicators(
    employee_id: int, month: int = 0,
        year: int = 0) -> EmployeeMonthIndicators:
    """
    Returns EmployeeWorkshiftsIndicators for employee
    """
    if not month or not year:
        month, year = timezone.now().month, timezone.now().year
    number_of_total_workshifts = get_employee_month_workshifts(
        employee_id, month, year).count()
    shortage_sum = get_employee_month_workshifts(
        employee_id, month, year).filter(
            cash_admin__id=employee_id, shortage_paid=False).aggregate(
                Sum('shortage')).get('shortage__sum', 0.0)
    rating_data=get_rating_data(employee_id, month, year)
    summary_earnings = _get_summary_earnings(employee_id, month, year,
                                             rating_data)
    number_of_verified_workshifts=get_employee_month_workshifts(
        employee_id, month, year, True).count()

    logger.info(f'Return employee indicators at {month}-{year}.')
    return EmployeeMonthIndicators(
        summary_earnings=summary_earnings,
        summary_shortage=shortage_sum,
        number_of_verified_workshifts=number_of_verified_workshifts,
        number_of_total_workshifts=number_of_total_workshifts,
        rating_data=rating_data
    )

