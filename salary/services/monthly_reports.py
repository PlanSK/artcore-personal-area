import datetime
import logging

from enum import Enum
from typing import NamedTuple

from django.db.models import QuerySet
from django.conf import settings

from salary.models import WorkingShift
from salary.services.earnings import Earnings


logger = logging.getLogger(__name__)


class RatingDataNotDefined(ValueError):
    pass


class EmployeeData(NamedTuple):
    id: int
    full_name: str
    shift_counter: int
    basic_revenues: float
    bonus_revenues: float
    shortage: float
    penalty: float
    average_revenue: float
    summary_bar_revenue: float
    average_bar_revenue: float
    summary_hookah_revenue: float
    average_hookah_revenue: float


class WorkshiftData(NamedTuple):
    cashier: dict
    hall_admin: dict


class EmployeeCategories(NamedTuple):
    cashier_list: list[EmployeeData]
    hall_admin_list: list[EmployeeData]


class MonthlyData(NamedTuple):
    employees: list[EmployeeData]
    shift_counter: int
    summary_basic_revenue: float
    summary_bonus_revenue: float
    summary_all_shortages: float
    summary_all_penalties: float


class Leader(NamedTuple):
    leader: EmployeeData
    total_sum: float


class AwardData(NamedTuple):
    cashiers_list: list[EmployeeData]
    hall_admin_list: list[EmployeeData]
    bar_leader: Leader | None
    hookah_leader: Leader | None
    cashiers_leader: Leader | None
    hall_admins_leader: Leader | None


class Category(NamedTuple):
    first: EmployeeData | None
    second: EmployeeData | None
    third: EmployeeData | None
    other: list


class EmployeeRatingPosition(Enum):
    ABSOLUTE_LEADER = 'абсолютный лидер'
    HOOKAH_LEADER = 'лидер по кальянам'
    BAR_LEADER = 'лидер по бару'
    AVERAGE_SUM_LEADER = 'лидер по средней выручке'
    NOT_LEADER = ''


class Rating(NamedTuple):
    special_rating: Category
    common_rating: Category
    position: EmployeeRatingPosition
    bonus: float


class FilteredRating(NamedTuple):
    bar_rating: Category
    hookah_rating: Category
    hall_admin_common_rating: Category
    cashier_common_rating: Category
    full_cashier_list: list
    full_hall_admin_list: list


def get_workshift_data(workshift: WorkingShift) -> WorkshiftData:
    """
    Returns WorkshiftData model with cashier and hall_admin dict's
    """
    cashier_earnings_data: Earnings = workshift.cashier_earnings
    hall_admin_earnings_data: Earnings = workshift.hall_admin_earnings
    
    cashier_dict = {
        'id': workshift.cash_admin.id,
        'name': workshift.cash_admin.get_full_name(),
        'basic_part': cashier_earnings_data.basic_part.summary,
        'bonus_part': cashier_earnings_data.bonus_part.summary,
        'shortage': cashier_earnings_data.shortage,
        'penalty': cashier_earnings_data.penalty,
        'revenue': workshift.game_zone_subtotal + \
            workshift.additional_services_revenue,
        'bar_revenue': workshift.bar_revenue,
    }
    hall_admin_dict = {
        'id': workshift.hall_admin.id,
        'name': workshift.hall_admin.get_full_name(),
        'basic_part': hall_admin_earnings_data.basic_part.summary,
        'bonus_part': hall_admin_earnings_data.bonus_part.summary,
        'penalty': hall_admin_earnings_data.penalty,
        'revenue': workshift.game_zone_subtotal + \
            workshift.additional_services_revenue,
        'hookah_revenue': workshift.hookah_revenue,
    }
    return WorkshiftData(cashier=cashier_dict, hall_admin=hall_admin_dict)


def get_employee_data_list(employee_list: list[dict]) -> list[EmployeeData]:
    """
    Returns list of EmployeeData Model from employee_list
    """

    employee_append_dict = {}
    employee_data_list = []
    keywords_dict = (
        ('summary_revenues', 'revenue'),
        ('basic_revenues', 'basic_part'),
        ('bonus_revenues', 'bonus_part'),
        ('shortage', 'shortage'),
        ('penalty', 'penalty'),
        ('summary_revenue', 'revenue'),
        ('summary_bar_revenue', 'bar_revenue'),
        ('summary_hookah_revenue', 'hookah_revenue')
    )

    for employee_data in employee_list:
        id = employee_data.get('id')
        current_employee: dict | None = employee_append_dict.get(id)
        if not current_employee:
            current_employee = employee_append_dict.setdefault(
                id, {'name': employee_data.get('name'), 'shift_counter': 0,}
            )
            current_employee.update(
                {key: [] for key, _ in keywords_dict}
            )
        current_employee['shift_counter'] += 1
        for where_key, from_key in keywords_dict:
            current_employee[where_key].append(
                employee_data.get(from_key, 0.0)
            )

    for id, id_data in employee_append_dict.items():
        summary_revenue = sum(id_data.get('summary_revenue'))
        shift_counter = id_data.get('shift_counter', 0)
        average_revenue = summary_revenue / id_data.get('shift_counter', 1)
        summary_bar_revenue = round(sum(id_data.get('summary_bar_revenue')), 2)
        summary_hookah_revenue = round(
            sum(id_data.get('summary_hookah_revenue')), 2)
        average_bar_revenue = average_hookah_revenue = 0.0
        if shift_counter:
            average_bar_revenue = summary_bar_revenue / shift_counter
            average_hookah_revenue = summary_hookah_revenue / shift_counter

        employee_data_list.append(
            EmployeeData(
                id=id,
                full_name=id_data.get('name'),
                shift_counter=shift_counter,
                basic_revenues=round(sum(id_data.get('basic_revenues')), 2),
                bonus_revenues=round(sum(id_data.get('bonus_revenues')), 2),
                shortage=round(sum(id_data.get('shortage')), 2),
                penalty=round(sum(id_data.get('penalty')), 2),
                average_revenue=round(average_revenue, 2),
                summary_bar_revenue=summary_bar_revenue,
                average_bar_revenue=round(average_bar_revenue, 2),
                summary_hookah_revenue=summary_hookah_revenue,
                average_hookah_revenue=round(average_hookah_revenue, 2)
            )
        )

    return employee_data_list


def get_employee_lists_by_categories(
        workshifts: QuerySet) -> EmployeeCategories:
    """
    Returns EmployeeCategories model from workshifts QuerySet
    """
    cashiers_data_list = []
    hall_admins_data_list = []

    for data in map(get_workshift_data, workshifts):
        cashiers_data_list.append(data.cashier)
        hall_admins_data_list.append(data.hall_admin)

    cashiers_list = get_employee_data_list(cashiers_data_list)
    hall_admins_list = get_employee_data_list(hall_admins_data_list)

    return EmployeeCategories(
        cashier_list=cashiers_list,
        hall_admin_list=hall_admins_list,
    )


def get_monthly_data_from_workshifts(workshifts: WorkingShift) -> MonthlyData:
    """
    Returns MonthlyData from workshifts with summary basic and bonus parts
    revenue and summary shortages, penalties.
    """
    categories_list = get_employee_lists_by_categories(workshifts)
    employee_data_list: list = (
        categories_list.cashier_list + categories_list.hall_admin_list
    )
    employee_data_list.sort(key=lambda x: x.shift_counter, reverse=True)

    monthly_summary_basic_part = 0.0
    monthly_summary_bonus_part = 0.0
    summary_shortages = 0.0
    summary_penalties = 0.0
    for employee in employee_data_list:
        monthly_summary_basic_part += employee.basic_revenues
        monthly_summary_bonus_part += employee.bonus_revenues
        summary_shortages += employee.shortage
        summary_penalties += employee.penalty
    
    return MonthlyData(
        employees=employee_data_list,
        shift_counter=len(workshifts),
        summary_basic_revenue=round(monthly_summary_basic_part, 2),
        summary_bonus_revenue=round(monthly_summary_bonus_part, 2),
        summary_all_shortages=round(summary_shortages, 2),
        summary_all_penalties=round(summary_penalties, 2)
    )


def get_monthly_workingshifts_queryset(month: int, year: int) -> QuerySet:
    """
    Returns a verified WorkingShift's QuerySet for the month and year
    """
    workshifts = WorkingShift.objects.select_related(
        'cash_admin__profile__position',
        'hall_admin__profile__position',
    ).filter(
        shift_date__month=month,
        shift_date__year=year,
        status=WorkingShift.WorkshiftStatus.VERIFIED
    )
    return workshifts


def get_monthly_report(month: int, year: int) -> MonthlyData:
    """
    Returns MonthlyData report for the month
    """
    workshifts = get_monthly_workingshifts_queryset(month=month, year=year)
    monthly_report = get_monthly_data_from_workshifts(workshifts)
    return monthly_report


def get_awards_data(month: int, year: int) -> AwardData:
    """
    Returns awards data for the month
    """
    workshifts = get_monthly_workingshifts_queryset(month=month, year=year)
    categories_list = get_employee_lists_by_categories(workshifts)

    bar_current_leader = None
    bar_max_revenue = 0.0
    cashier_current_leader = None
    cash_admin_max_avg_revenue = 0.0
    default_shifts_number = settings.MINIMAL_WORKSHIFTS_NUMBER
    avg_bar_limit = settings.AVERAGE_BAR_REVENUE_CRITERIA
    avg_hookah_limit = settings.AVERAGE_HOOKAH_REVENUE_CRITERIA
    filtered_cashier_list = [
        employee for employee in categories_list.cashier_list
        if employee.shift_counter >= default_shifts_number
    ]
    for employee in filtered_cashier_list:
        if (bar_max_revenue < employee.summary_bar_revenue
                and employee.average_bar_revenue >= avg_bar_limit):
            bar_max_revenue = employee.summary_bar_revenue
            bar_current_leader = Leader(
                leader=employee,
                total_sum=employee.summary_bar_revenue
            )
        if cash_admin_max_avg_revenue < employee.average_revenue:
            cash_admin_max_avg_revenue = employee.average_revenue
            cashier_current_leader = Leader(
                leader=employee,
                total_sum=employee.average_revenue
            )

    hookah_current_leader = None
    hookah_max_revenue = 0.0
    hall_admins_current_leader = None
    hall_admin_max_avg_revenue = 0.0
    filtered_hall_admin_list = [
        employee for employee in categories_list.hall_admin_list
        if employee.shift_counter >= default_shifts_number
    ]
    for employee in filtered_hall_admin_list:
        if (hookah_max_revenue < employee.summary_hookah_revenue
                and employee.average_hookah_revenue >= avg_hookah_limit):
            hookah_max_revenue = employee.summary_hookah_revenue
            hookah_current_leader = Leader(
                leader=employee,
                total_sum=employee.summary_hookah_revenue
            )
        if hall_admin_max_avg_revenue < employee.average_revenue:
            hall_admin_max_avg_revenue = employee.average_revenue
            hall_admins_current_leader = Leader(
                leader=employee,
                total_sum=employee.average_revenue
            )

    categories_list.cashier_list.sort(
        key=lambda x: x.summary_bar_revenue, reverse=True
    )
    categories_list.hall_admin_list.sort(
        key=lambda x: x.summary_hookah_revenue, reverse=True
    )

    return AwardData(
        cashiers_list=categories_list.cashier_list,
        hall_admin_list=categories_list.hall_admin_list,
        bar_leader=bar_current_leader,
        hookah_leader=hookah_current_leader,
        cashiers_leader=cashier_current_leader,
        hall_admins_leader=hall_admins_current_leader
    )


def get_categories_from_list(employee_list: list) -> Category:
    """
    Returns Category model with EmployeeData by place
    """
    match employee_list:
        case (first, second, third, *other):
            return Category(first=first, second=second,
                            third=third, other=other)
        case (first, second, *other):
            return Category(first=first, second=second,
                            third=None, other=other)
        case (first, *other):
            return Category(first=first, second=None,
                            third=None, other=other)
        case ():
            return Category(first=None, second=None,
                            third=None, other=[])
        case _:
            logging.error('Unknown incoming data for get_categiries_from_list')
            raise ValueError(f'Unknown data error in {employee_list}')


def get_employee_rating_position(
    special: EmployeeData | None, common: EmployeeData | None,
        employee_id: int, is_cashier: bool = False) -> EmployeeRatingPosition:
    """
    Returns Employee position in the rating
    """

    special_category_leader = False
    common_category_leader = False
    default_shifts_number = settings.MINIMAL_WORKSHIFTS_NUMBER

    if (special and special.id == employee_id
            and special.shift_counter >= default_shifts_number):
        special_category_leader = True
    if (common and common.id == employee_id 
            and common.shift_counter >= default_shifts_number):
        common_category_leader = True

    if special_category_leader and common_category_leader:
        return EmployeeRatingPosition.ABSOLUTE_LEADER
    elif special_category_leader:
        if is_cashier:
            return EmployeeRatingPosition.BAR_LEADER
        else:
            return EmployeeRatingPosition.HOOKAH_LEADER
    elif common_category_leader:
        return EmployeeRatingPosition.AVERAGE_SUM_LEADER
    else:
        return EmployeeRatingPosition.NOT_LEADER


def get_rating_bonus(leader_type: Leader) -> float:
    """
    Returns float bonus for leader position in rating
    """
    bonus = 0.0
    if leader_type == EmployeeRatingPosition.ABSOLUTE_LEADER:
        bonus = (settings.SPECIAL_CATEGORY_BONUS +
                 settings.COMMON_CATEGORY_BONUS)
    elif (leader_type == EmployeeRatingPosition.BAR_LEADER
            or leader_type == EmployeeRatingPosition.HOOKAH_LEADER):
        bonus = settings.SPECIAL_CATEGORY_BONUS
    elif leader_type == EmployeeRatingPosition.AVERAGE_SUM_LEADER:
        bonus = settings.COMMON_CATEGORY_BONUS

    return bonus


def _sort_list_by_average_revenue(employee_list: list) -> None:
    """
    Sort list by average_revenue
    """
    employee_list.sort(key=lambda x: x.average_revenue, reverse=True)


def get_filtered_rating_data(month: int, year: int) -> FilteredRating:
    """
    Returns filtered Rating data from awards data
    """
    award_data = get_awards_data(year=year, month=month)
    avg_bar_limit = settings.AVERAGE_BAR_REVENUE_CRITERIA
    avg_hookah_limit = settings.AVERAGE_HOOKAH_REVENUE_CRITERIA
    minimal_shift_number = settings.MINIMAL_WORKSHIFTS_NUMBER

    minimal_shift_filtered_cashiers_list = [
        employee for employee in award_data.cashiers_list
        if employee.shift_counter >= minimal_shift_number
    ]
    minimal_shift_filtered_hall_admin_list = [
        employee for employee in award_data.hall_admin_list
        if employee.shift_counter >= minimal_shift_number
    ]
    avg_bar_revenue_filtered_list = [
        employee for employee in minimal_shift_filtered_cashiers_list
        if employee.average_bar_revenue >= avg_bar_limit
    ]
    avg_hookah_revenue_filtered_list = [
        employee for employee in minimal_shift_filtered_hall_admin_list
        if employee.average_hookah_revenue >= avg_hookah_limit
            and employee.shift_counter >= minimal_shift_number
    ]

    bar_rating = get_categories_from_list(avg_bar_revenue_filtered_list)
    hookah_rating = get_categories_from_list(avg_hookah_revenue_filtered_list)

    _sort_list_by_average_revenue(minimal_shift_filtered_cashiers_list)
    cashiers_rating = get_categories_from_list(
        minimal_shift_filtered_cashiers_list)
    _sort_list_by_average_revenue(minimal_shift_filtered_hall_admin_list)
    hall_admins_rating = get_categories_from_list(
        minimal_shift_filtered_hall_admin_list)

    return FilteredRating(
        bar_rating=bar_rating,
        hookah_rating=hookah_rating,
        hall_admin_common_rating=hall_admins_rating,
        cashier_common_rating=cashiers_rating,
        full_cashier_list=award_data.cashiers_list,
        full_hall_admin_list=award_data.hall_admin_list
    )


def _get_employee_rating_data(employee_id: int,
                              is_cashier: bool,
                              month: int = datetime.date.today().month,
                              year: int = datetime.date.today().year
    ) -> Rating:
    """
    Define and returns Rating data from awards data.
    """
    all_filtered_categories = get_filtered_rating_data(month=month, year=year)

    if is_cashier and tuple(filter(lambda x: x.id == employee_id,
                all_filtered_categories.full_cashier_list)):
        special_rating=all_filtered_categories.bar_rating
        common_rating=all_filtered_categories.cashier_common_rating
    elif tuple(filter(lambda x: x.id == employee_id,
                all_filtered_categories.full_hall_admin_list)):
        special_rating=all_filtered_categories.hookah_rating
        common_rating=all_filtered_categories.hall_admin_common_rating
    else:
        raise RatingDataNotDefined

    position = get_employee_rating_position(
        special=special_rating.first,
        common=common_rating.first,
        employee_id=employee_id,
        is_cashier=is_cashier
    )
    return Rating(
        special_rating=special_rating,
        common_rating=common_rating,
        position=position,
        bonus=get_rating_bonus(position)
    )


def get_rating_data(employee_id: int,
                    is_cashier: bool,
                    month: int = datetime.date.today().month,
                    year: int = datetime.date.today().year) -> Rating | None:
    """
    Returns Rating data for the employee by id or None if employee rating
    status not defined.
    """
    rating_data = None
    try:
        rating_data = _get_employee_rating_data(employee_id, is_cashier,
                                                month, year)
    except RatingDataNotDefined:
        logger.warning(
            f'Employee id {employee_id} rating position is not found.')
    except ValueError as excexption:
        logger.exception(f'Value error: {excexption}.')

    return rating_data
