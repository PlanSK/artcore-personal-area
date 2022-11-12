import calendar
import datetime
import logging

from typing import NamedTuple

from django.contrib.auth.models import User
from django.db.models import QuerySet, Q, Sum

from salary.services.shift_calendar import get_planed_workshifts_list
from salary.services.monthly_reports import Rating, get_rating_data
from salary.models import WorkingShift


logger = logging.getLogger(__name__)


class EmployeeMonthIndicators(NamedTuple):
    summary_earnings: float
    summary_shortage: float
    number_of_verified_workshifts: int
    number_of_total_workshifts: int
    rating_data: Rating | None


def check_permission_to_close(
        user: User, date: datetime.date = datetime.date.today()) -> bool:
    """
    Check permissions and requesting days list from schedule and returning
    True if yesterday date in this list.
    """
    logger.info(f'Start check permission for user {user.id} with {date}.')
    if user.has_perm('salary.add_workingshift'):
        logger.debug(f'User has permissions <add_workingshift>.')
        yesterday = date - datetime.timedelta(days=1)
        logger.debug(f'Yesterday date is {yesterday}. Get planed workshifts.')
        planed_shifts = get_planed_workshifts_list(
            user=user,
            year=yesterday.year,
            month=yesterday.month
        )
        logger.debug(f'Planed days: {planed_shifts}.')
        if yesterday.day in planed_shifts:
            logger.info(
                f'User {user.id} has permissions for close current workshift.')
            return True
    logger.info(
        f'User {user.id} has no permissions for close current workshift.')
    return False


def notification_of_upcoming_shifts(
        user: User, date: datetime.date = datetime.date.today()) -> bool:
    """
    Returning True if tomorrow in days list from schedule.
    """
    logger.debug(f'Prepare notofication for user {user.id} with {date}.')
    tomorrow = date + datetime.timedelta(days=1)
    logger.debug(f'Tomorrow date is {tomorrow}.')
    planed_shifts = get_planed_workshifts_list(
            user=user,
            year=tomorrow.year,
            month=tomorrow.month
    )
    logger.debug(f'Planed days: {planed_shifts}.')
    if tomorrow.day in planed_shifts:
        logger.debug(f'User {user.id} can see notification.')
        return True

    logger.debug(f'Notification for user {user.id} do not show.')
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
    employee_id: int, month: int = datetime.date.today().month,
        year: int = datetime.date.today().year) -> EmployeeMonthIndicators:
    """
    Returns EmployeeWorkshiftsIndicators for employee
    """
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

    return EmployeeMonthIndicators(
        summary_earnings=summary_earnings,
        summary_shortage=shortage_sum,
        number_of_verified_workshifts=number_of_verified_workshifts,
        number_of_total_workshifts=number_of_total_workshifts,
        rating_data=rating_data
    )

