import datetime
import logging

from typing import NamedTuple

from django.contrib.auth.models import User
from django.db.models import QuerySet, Q, Sum
from django.shortcuts import get_object_or_404
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


class UnclosedWorkshifts(NamedTuple):
    unverified_number: int
    wait_fix_number: int
    unclosed_number: int


def _is_date_day_exists_in_plan(user_id: int,
                           check_date: datetime.date) -> bool:
    """Returns True if day from check_date exists
    in the plan else returns False.
    """
    planed_shifts_days_tuple = get_planed_workshifts_days_list(
        user_id=user_id, month=check_date.month, year=check_date.year)
    logger.debug(f'Planed days: {planed_shifts_days_tuple}.')
    if check_date in planed_shifts_days_tuple:
        logger.debug(f'{check_date} exists in {planed_shifts_days_tuple}.')
        return True

    logger.debug(f'{check_date} is not exists in the plan.')
    return False


def _get_date_with_offset(
        offset: int,
        current_date: datetime.date | None = None) -> datetime.date:
    """Returns date with offset."""
    if not current_date:
        date = timezone.localdate(timezone.now())
        logger.debug(f'Set default value of current_date: {date}.')
    else:
        date = current_date

    if offset > 0:
        return date + datetime.timedelta(offset)
    elif offset < 0:
        return date - datetime.timedelta(abs(offset))
    else:
        return date


def notification_of_upcoming_shifts(
        user_id: int, date_before: datetime.date | None = None) -> bool:
    """Returning True if tomorrow in days list from schedule."""
    tomorrow = _get_date_with_offset(1, date_before)
    logger.info(
        f'Start checking for permissions to show notification. '
        f'User: {user_id}. Tomorrow value: {tomorrow}.'
    )

    if _is_date_day_exists_in_plan(user_id, tomorrow):
        logger.info(f'User {user_id} can see notification.')
        return True

    logger.info(f'Notification for user {user_id} do not show.')
    return False


def get_missed_dates_tuple() -> tuple[datetime.date]:
    """Returns tuple with missed dates of unclosed workshifts."""
    current_date = timezone.localdate(timezone.now())
    year, month = current_date.year, current_date.month
    last_day_of_month = current_date.day
    logger.debug(f'"missed dates" current date: {current_date}')

    exists_workshifts_dates = WorkingShift.objects.filter(
        shift_date__month=month, shift_date__year=year,
        shift_date__day__lte=last_day_of_month).dates('shift_date', 'day')
    logger.debug(f'Exists workshifts dates: {exists_workshifts_dates}')
    month_dates = [
        datetime.date(year, month, day)
        for day in range(1, last_day_of_month + 1)
    ]
    missed_dates_tuple = tuple([
        date for date in month_dates
        if date not in exists_workshifts_dates
    ])
    logger.info(f'Missed dates tuple: {missed_dates_tuple}')

    return missed_dates_tuple


def get_employee_unclosed_workshifts_dates(
        user_id: int) -> tuple[datetime.date]:
    """Returns tuple with missed dates of employee unclosed workshifts."""
    requested_user = get_object_or_404(User, id=user_id)
    if not requested_user.has_perm('salary.add_workingshift'):
        logger.info(
            f'User {requested_user.username} has no permissions '
            f'to close workshifts.'
        )
        return tuple()

    current_date = timezone.localdate(timezone.now())
    logger.debug(
        f'"employee_unclosed_workshifts" current date: {current_date}')
    year, month = current_date.year, current_date.month

    missed_dates = get_missed_dates_tuple()
    planed_shift_closed_dates = [
        _get_date_with_offset(1, planed_date)
        for planed_date in get_planed_workshifts_days_list(user_id, month,
                                                           year)
    ]
    logger.debug(f'User allowed to close dates: {planed_shift_closed_dates}')

    employee_unclosed_workshifts_dates = [
        date for date in missed_dates
        if date in planed_shift_closed_dates
    ]

    first_month_date = datetime.date(year, month, 1)
    if first_month_date in missed_dates:
        logger.debug(
            f'Check permissoins to close first day {first_month_date}.')
        last_day_of_last_month = _get_date_with_offset(-1, first_month_date)
        last_month_planed_days = get_planed_workshifts_days_list(
            user_id, last_day_of_last_month.month, last_day_of_last_month.year)
        if (last_month_planed_days
                and last_month_planed_days[-1] == last_day_of_last_month):
            employee_unclosed_workshifts_dates.append(first_month_date)
    logger.info(
        f'User unclosed workshift dates: {employee_unclosed_workshifts_dates}')
    return tuple(employee_unclosed_workshifts_dates)


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
        return employee_month_workshifts.filter(
            status=WorkingShift.WorkshiftStatus.VERIFIED)

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


def get_unclosed_workshift_number() -> UnclosedWorkshifts:
    """
    Returns number of unclosed workshifts 
    """
    unclosed_workshifts_number = WorkingShift.objects.exclude(
            status=WorkingShift.WorkshiftStatus.VERIFIED).count()
    wait_fix_workshifts_number = WorkingShift.objects.filter(
            status=WorkingShift.WorkshiftStatus.WAIT_CORRECTION).count()
    unverified_workshifts_number = unclosed_workshifts_number - \
        wait_fix_workshifts_number
    return UnclosedWorkshifts(unverified_number=unverified_workshifts_number,
                              wait_fix_number=wait_fix_workshifts_number,
                              unclosed_number=unclosed_workshifts_number)
