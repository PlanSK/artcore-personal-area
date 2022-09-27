import datetime

from django.contrib.auth.models import User
from django.conf import settings
from typing import NamedTuple, Union

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


# Earnings block moved from models.py
class WorkshiftData(NamedTuple):
    shift_date: datetime.date
    bar_revenue: float
    game_zone_revenue: float
    vr_revenue: float
    hookah_revenue: float
    hall_cleaning: bool
    shortage: float
    shortage_paid: bool
    publication: bool
    admin_penalty: float
    cashier_penalty: float


class BasicPart(NamedTuple):
    salary: Union[float, None]
    experience: float
    attestation: float
    summary: float


class PercentValue(NamedTuple):
    percent: float
    value: float


class Revenues(NamedTuple):
    bar: PercentValue
    game_zone: PercentValue
    vr: PercentValue


class BonusPart(NamedTuple):
    award: float
    revenues: Revenues
    publication: float
    cleaning: float
    hookah: float
    summary: float


class Earnings(NamedTuple):
    basic_part: BasicPart
    bonus_part: BonusPart
    penalty: float
    retention: float
    estimate_earnings: float
    before_shortage: float
    final_earnings: float


def get_experience_bonus(employment_date: datetime.date,
                         shift_date: datetime.date) -> float:
    """
    Return REQUIRED_EXPERIENCE if experience more than 90 days or 0.0 if less
    """
    current_experience = (shift_date - employment_date).days
    if settings.REQUIRED_EXPERIENCE <= current_experience:
        return settings.EXPERIENCE_BONUS

    return 0.0


def get_attestation_bonus(attestation_date: datetime.date,
                          shift_date: datetime.date) -> float:
    """
    Return ATTESTATION_BONUS if attestation date is defined
    and older than shift date
    """
    if attestation_date and attestation_date <= shift_date:
        return settings.ATTESTATION_BONUS

    return 0.0


def get_basic_part(employee: User, workshift_date: datetime.date) -> BasicPart:
    """
    Return named tuple with basic part values: salary, experience, attestation
    and summry (sum of all values)
    """
    salary: Union[float, None] = employee.profile.position.salary,
    experience = 0.0
    attestation = 0.0
    summary = 0.0
    if salary:
        experience = get_experience_bonus(
            employee.profile.employment_date,
            workshift_date
        )
        attestation = get_attestation_bonus(
            employee.profile.attestation_date,
            workshift_date
        )
        summary: float = sum((salary, experience, attestation))
    return BasicPart(
        salary=salary,
        experience=experience,
        attestation=attestation,
        summary=summary
    )


def get_percent_of_revenue(
        value: float,
        criterias: tuple[tuple[int, float], ...]) -> PercentValue:
    """
    Return right value of ratio, and calculated revenue with current ratio
    """
    current_ratio: float = 0.0
    for max_value, ratio in criterias:
        if value >= max_value:
            current_ratio = ratio
        else:
            break

    return PercentValue(
        percent=current_ratio, value=value * current_ratio
    )


def get_calculated_revenues(workshift_data: WorkshiftData,
                            is_cashier: bool = False) -> Revenues:
    """
    Return calculated revenues according to the criteria
    """
    criteria = settings.ADMIN_BONUS_CRITERIA
    if is_cashier:
        criteria = settings.CASHIER_BONUS_CRITERIA

    return Revenues(
        bar=get_percent_of_revenue(
            workshift_data.bar_revenue,
            criteria.bar
        ),
        game_zone=get_percent_of_revenue(
            workshift_data.game_zone_revenue,
            criteria.game_zone
        ),
        vr=get_percent_of_revenue(
            workshift_data.vr_revenue,
            criteria.vr
        )
    )


def get_current_earnings(employee: User,
                         workshift_data: WorkshiftData,
                         is_cashier: bool = False) -> Earnings:
    """
    Return employee earnings
    """
    basic_part = get_basic_part(employee=employee,
                                workshift_date=workshift_data.shift_date)
    calculated_revenues = get_calculated_revenues(workshift_data, is_cashier)
