import datetime

from dataclasses import dataclass
from typing import NamedTuple

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class WorkshiftData(NamedTuple):
    shift_date: datetime.date
    bar_revenue: float
    game_zone_revenue: float
    additional_services_revenue: float
    hookah_revenue: float
    hall_cleaning: bool
    shortage: float
    shortage_paid: bool
    publication: bool
    admin_penalty: float
    cashier_penalty: float


class BasicPart(NamedTuple):
    salary: float
    experience: float
    attestation: float
    summary: float


class PercentValue(NamedTuple):
    percent: float
    value: float


class Revenues(NamedTuple):
    bar: PercentValue
    game_zone: PercentValue
    additional_services: PercentValue
    summary: float


class BonusPart(NamedTuple):
    award: float
    revenues: Revenues
    publication: float
    cleaning: float
    hookah: PercentValue
    summary: float


class Earnings(NamedTuple):
    basic_part: BasicPart
    bonus_part: BonusPart
    penalty: float
    shortage: float
    retention: float
    estimated_earnings: float
    before_shortage: float
    final_earnings: float


@dataclass
class Penalties:
    cash_admin_penalty: float = 0.0
    hall_admin_penalty: float = 0.0


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
    if (attestation_date and attestation_date <= shift_date
            and settings.ATTESTATION_ENABLED):
        return settings.ATTESTATION_BONUS

    return 0.0


def get_basic_part(employee: User, workshift_date: datetime.date) -> BasicPart:
    """
    Return named tuple with basic part values: salary, experience, attestation
    and summry (sum of all values)
    """
    salary = employee.profile.position.position_salary
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
        summary = sum((salary, experience, attestation))
    return BasicPart(
        salary=salary,
        experience=experience,
        attestation=attestation,
        summary=round(summary, 2)
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
        percent=round(current_ratio * 100, 2),
        value=round(value * current_ratio, 2)
    )


def get_calculated_revenues(workshift_data: WorkshiftData,
                            is_cashier: bool = False) -> Revenues:
    """
    Return calculated revenues according to the criteria
    """
    summary = 0.0
    criteria = settings.ADMIN_BONUS_CRITERIA
    if is_cashier:
        criteria = settings.CASHIER_BONUS_CRITERIA
    bar = get_percent_of_revenue(
        workshift_data.bar_revenue,
        criteria.bar
    )
    game_zone = get_percent_of_revenue(
        workshift_data.game_zone_revenue,
        criteria.game_zone
    )
    additional_services = get_percent_of_revenue(
        workshift_data.additional_services_revenue,
        criteria.additional_services
    )
    summary = sum((bar.value, game_zone.value, additional_services.value))

    return Revenues(
        bar=bar,
        game_zone=game_zone,
        additional_services=additional_services,
        summary=round(summary, 2)
    )


def get_hookah_earnings(workshift_data: WorkshiftData) -> PercentValue:
    """
    Return hookah calculated earnings and percent
    """
    return PercentValue(
        percent=round(settings.HOOKAH_BONUS_RATIO * 100, 2),
        value=round(
            workshift_data.hookah_revenue * settings.HOOKAH_BONUS_RATIO, 2
        ))


def get_bonus_part(workshift_data: WorkshiftData,
                   is_cashier: bool = False) -> BonusPart:
    """
    Return the bonus part of earnings.
    """
    award = settings.DISCIPLINE_AWARD
    revenues = get_calculated_revenues(workshift_data, is_cashier)
    publication = 0.0
    cleaning = 0.0
    hookah = PercentValue(percent=0.0, value=0.0)
    summary = 0.0
    if workshift_data.publication and settings.PUBLICATION_ENABLED:
        publication = settings.PUBLICATION_BONUS
    if not is_cashier:
        hookah = get_hookah_earnings(workshift_data)
        if workshift_data.hall_cleaning:
            cleaning = settings.HALL_CLEANING_BONUS
    summary = sum(
        (award, publication, cleaning, hookah.value, revenues.summary)
    )

    return BonusPart(
        award=award, revenues=revenues, publication=publication,
        cleaning=cleaning, hookah=hookah, summary=round(summary, 2)
    )


def get_current_earnings(employee: User,
                         workshift_data: WorkshiftData,
                         is_cashier: bool = False) -> Earnings:
    """
    Return employee earnings
    """
    basic_part = get_basic_part(employee=employee,
                                workshift_date=workshift_data.shift_date)
    bonus_part = get_bonus_part(workshift_data=workshift_data,
                                is_cashier=is_cashier)
    penalty = workshift_data.admin_penalty
    shortage = 0.0
    if is_cashier:
        penalty = workshift_data.cashier_penalty
    remaining_bonus_part = 0.0
    if bonus_part.summary > penalty:
            remaining_bonus_part = bonus_part.summary - penalty
    retention = round(bonus_part.summary - remaining_bonus_part, 2)
    estimated_earnings = round(bonus_part.summary + basic_part.summary, 2)
    final_earnings = round(remaining_bonus_part + basic_part.summary, 2)
    before_shortage = final_earnings

    if (is_cashier and
            workshift_data.shortage and not workshift_data.shortage_paid):
        shortage = workshift_data.shortage
        final_earnings = round(final_earnings - workshift_data.shortage * 2, 2)

    return Earnings(
        basic_part=basic_part, bonus_part=bonus_part,
        penalty=penalty, shortage=shortage, retention=retention,
        estimated_earnings=estimated_earnings, before_shortage=before_shortage,
        final_earnings=final_earnings
    )


def get_total_revenue(*args) -> float:
    """Returns sum of revenue values"""
    return sum(args) if sum(args) else 0.0


def get_game_zone_subtotal(game_zone_revenue: float,
                           game_zone_error: float) -> float:
    """Returns calculation subtotal for game_zone sum"""
    if game_zone_revenue >= game_zone_error:
        return round(game_zone_revenue - game_zone_error, 2)
    return 0.0


def get_workshift_penalties(misconduct_queryset: models.QuerySet,
                            cash_admin_id: int,
                            hall_admin_id: int) -> Penalties:
    """Returns penalties for employees from Misconsucts"""
    current_penalties = Penalties()
    for misconduct in misconduct_queryset:
        if misconduct.intruder.id == cash_admin_id:
            current_penalties.cash_admin_penalty += misconduct.penalty
        elif misconduct.intruder.id == hall_admin_id:
            current_penalties.hall_admin_penalty += misconduct.penalty
    return current_penalties


def get_costs_sum(costs_queryset: models.QuerySet) -> float:
    """Returns sum of costs for workshift"""
    costs_sum = costs_queryset.aggregate(
        models.Sum('cost_sum')).get('cost_sum__sum')
    if isinstance(costs_sum, float):
        return costs_sum
    return 0.0


def get_errors_sum(errors_queryset: models.QuerySet) -> float:
    """Returns sum of costs for workshift"""
    errors_sum = errors_queryset.aggregate(
        models.Sum('error_sum')).get('error_sum__sum')
    if isinstance(errors_sum, float):
        return errors_sum
    return 0.0
