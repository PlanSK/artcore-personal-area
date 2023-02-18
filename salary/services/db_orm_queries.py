import datetime
import logging

from django.db.models import QuerySet, Q
from django.contrib.auth.models import User
from salary.models import WorkingShift


logger = logging.getLogger(__name__)


def get_user_full_name_from_db(user_id: int) -> str:
    """Returns full employee name from db"""
    employee_full_name = ''
    try:
        employee_full_name = User.objects.get(pk=user_id).get_full_name()
    except User.DoesNotExist:
        logger.warning(
            f'Error getting full name from db: '
            f'User with id {user_id} does not exist.'
        )
    except Exception as exception:
        logger.warning(f'Error getting full name from db: {exception}')

    return employee_full_name


def get_user_month_workshifts(user_id: int, year: int, month: int) -> QuerySet:
    """
    Returns a QuerySet with shifts in the specified month of the year.
    """

    return WorkingShift.objects.select_related(
            'hall_admin__profile__position',
            'cash_admin__profile__position'
        ).filter(
            shift_date__month=month,
            shift_date__year=year,
        ).filter(
            Q(cash_admin__pk=user_id) | Q(hall_admin__pk=user_id)
        ).order_by('shift_date')


def has_cashier_permissions(employee_full_name: str) -> bool:
    """Returns True if employee is found in datebase
    and has permissions for add workshift.
    """
    last_name, first_name = employee_full_name.split()
    try:
        current_employee = User.objects.get(last_name=last_name,
                                            first_name=first_name)
    except User.DoesNotExist:
        logger.warning(f'{current_employee} is not found in datebase.')
        return False
    else:
        return current_employee.has_perm('salary.add_workingshift')


def get_users_full_names_list_from_db() -> list[str]:
    """Returns list with full names from db."""
    user_name_tuples_list = User.objects.all().values_list('last_name',
                                                           'first_name')
    user_full_names_list = [
        ' '.join(names_tuple) for names_tuple in user_name_tuples_list
    ]
    return user_full_names_list


def is_workshift_exists(day: datetime.date) -> bool:
    """Returns True if workshift on day is exists"""
    return WorkingShift.objects.filter(shift_date=day).exists()
