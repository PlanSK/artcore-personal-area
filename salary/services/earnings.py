import datetime

from django.contrib.auth.models import User
from django.conf import settings
from typing import NamedTuple


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
    vr: PercentValue
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
    vr = get_percent_of_revenue(
        workshift_data.vr_revenue,
        criteria.vr
    )
    summary = sum((bar.value, game_zone.value, vr.value))

    return Revenues(
        bar=bar,
        game_zone=game_zone,
        vr=vr,
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
    if workshift_data.publication:
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
