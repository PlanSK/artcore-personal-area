from django.db.models import QuerySet
from enum import Enum
import logging
from typing import NamedTuple

from salary.models import WorkingShift
from salary.services.earnings import Earnings


logger = logging.getLogger(__name__)


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
    summary_hookah_revenue: float


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


class LeaderType(Enum):
    ABSOLUTE = 'абсолютный лидер'
    HOOKAH = 'лидер по кальянам'
    BAR = 'лидер по бару'
    AVERAGE = 'лидер по средней выручке'
    NOT_LEADER = ''


class Rating(NamedTuple):
    special_rating: Category
    common_rating: Category
    position: LeaderType


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
        'revenue': workshift.game_zone_subtotal + workshift.vr_revenue,
        'bar_revenue': workshift.bar_revenue,
        'hookah_revenue': 0.0,
    }
    hall_admin_dict = {
        'id': workshift.hall_admin.id,
        'name': workshift.hall_admin.get_full_name(),
        'basic_part': hall_admin_earnings_data.basic_part.summary,
        'bonus_part': hall_admin_earnings_data.bonus_part.summary,
        'shortage': 0.0,
        'penalty': hall_admin_earnings_data.penalty,
        'revenue': workshift.game_zone_subtotal + workshift.vr_revenue,
        'bar_revenue': 0.0,
        'hookah_revenue': workshift.hookah_revenue,
    }
    return WorkshiftData(cashier=cashier_dict, hall_admin=hall_admin_dict)


def get_employee_data_list(employee_list: list) -> list[EmployeeData]:
    """
    Returns list of EmployeeData Model from employee_list
    """
    employee_append_dict = {}
    employee_data_list = []
    for employee_data in employee_list:
        current_employee = employee_append_dict.get(employee_data['id'])
        if current_employee:
            current_employee['shift_counter'] += 1
            current_employee['summary_revenues'].append(
                employee_data.get('revenue'))
            current_employee['basic_revenues'].append(
                employee_data.get('basic_part'))
            current_employee['bonus_revenues'].append(
                employee_data.get('bonus_part')
            )
            current_employee['shortage'].append(employee_data.get('shortage'))
            current_employee['penalty'].append(employee_data.get('penalty'))
            current_employee['average_revenue'].append(
                employee_data.get('revenue'))
            current_employee['summary_bar_revenue'].append(
                employee_data.get('bar_revenue'))
            current_employee['summary_hookah_revenue'].append(
                employee_data.get('hookah_revenue')
            )
        else:
            employee_append_dict.update(
                {
                    employee_data['id']: {
                        'name': employee_data.get('name'),
                        'shift_counter': 1,
                        'summary_revenues': [employee_data.get('revenue')],
                        'basic_revenues': [employee_data.get('basic_part')],
                        'bonus_revenues': [employee_data.get('bonus_part')],
                        'shortage': [employee_data.get('shortage')],
                        'penalty': [employee_data.get('penalty')],
                        'average_revenue': [employee_data.get('revenue')],
                        'summary_bar_revenue': [
                            employee_data.get('bar_revenue')
                        ],
                        'summary_hookah_revenue': [
                            employee_data.get('hookah_revenue')
                        ],
                    }
                }
            )
    for id, id_data in employee_append_dict.items():
        summary_revenue = sum(id_data['average_revenue'])
        average_revenue = summary_revenue / id_data['shift_counter']
        employee_data_list.append(
            EmployeeData(
                id=id,
                full_name=id_data['name'],
                shift_counter=id_data['shift_counter'],
                basic_revenues=round(sum(id_data['basic_revenues']), 2),
                bonus_revenues=round(sum(id_data['bonus_revenues']), 2),
                shortage=round(sum(id_data['shortage']), 2),
                penalty=round(sum(id_data['penalty']), 2),
                average_revenue=round(average_revenue, 2),
                summary_bar_revenue=round(
                    sum(id_data['summary_bar_revenue']), 2),
                summary_hookah_revenue=round(
                    sum(id_data['summary_hookah_revenue']), 2)
            )
        )

    return employee_data_list


def get_employee_workshift_data_list(
        workshifts: QuerySet) -> EmployeeCategories:

    workshifts_data_map = map(get_workshift_data, workshifts)

    cashiers_data_list = [data.cashier for data in workshifts_data_map]
    hall_admin_data_list = [data.cashier for data in workshifts_data_map]

    cashiers_list = get_employee_data_list(cashiers_data_list)
    hall_admins_list = get_employee_data_list(hall_admin_data_list)

    return EmployeeCategories(
        cashier_list=cashiers_list,
        hall_admin_list=hall_admins_list,
    )


def analyze_workshift_data(workshifts: WorkingShift) -> MonthlyData:

    categories_list = get_employee_workshift_data_list(workshifts)
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


def get_queryset_data(month: int, year: int) -> QuerySet:
    workshifts = WorkingShift.objects.select_related(
        'cash_admin__profile__position',
        'hall_admin__profile__position',
    ).filter(
        shift_date__month=month,
        shift_date__year=year,
        is_verified=True
    )
    return workshifts


def get_monthly_report(month: int, year: int) -> MonthlyData:
    workshifts = get_queryset_data(month=month, year=year)
    return analyze_workshift_data(workshifts)


def get_awards_data(month: int, year: int) -> AwardData:
    workshifts = get_queryset_data(month=month, year=year)
    categories_list = get_employee_workshift_data_list(workshifts)

    bar_current_leader = None
    bar_max_revenue = 0.0
    cashier_current_leader = None
    cash_admin_max_avg_revenue = 0.0

    for employee in filter(lambda x: x.shift_counter >= 4,
                           categories_list.cashier_list):
        if bar_max_revenue < employee.summary_bar_revenue:
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
    for employee in filter(lambda x: x.shift_counter >= 4,
                           categories_list.hall_admin_list):
        if hookah_max_revenue < employee.summary_hookah_revenue:
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


def get_position_type(
    special: EmployeeData | None, common: Category | None, employee_id: int,
        is_cashier: bool = False) -> LeaderType:

    special_category_leader = False
    common_category_leader = False

    if special and special.employee.id == employee_id:
        special_category_leader = True
    if common and common.employee.id == employee_id:
        common_category_leader = True

    if special_category_leader and common_category_leader:
        return LeaderType.ABSOLUTE
    elif special_category_leader:
        return LeaderType.BAR if is_cashier else LeaderType.HOOKAH
    elif common_category_leader:
        return LeaderType.AVERAGE
    else:
        return LeaderType.NOT_LEADER


def get_rating_data(award_data: AwardData, employee_id: int) -> Rating:
    if tuple(filter(lambda x: x.employee.id == employee_id,
                award_data.cashiers_list)):
        bar_rating = get_categories_from_list(award_data.cashiers_list)
        cashiers_revenue = sorted(
            award_data.cashiers_list,
            key=lambda x: x.average_revenue,
            reverse=True
        )
        cashiers_rating = get_categories_from_list(cashiers_revenue)
        position = get_position_type(
            special=bar_rating.first,
            common=cashiers_rating.first,
            employee_id=employee_id,
            is_cashier=True
        )
        return Rating(
            special_rating=bar_rating,
            common_rating=cashiers_rating,
            position=position
        )
    elif tuple(filter(lambda x: x.employee.id == employee_id,
                award_data.hall_admin_list)):
        hookah_rating = get_categories_from_list(award_data.hall_admin_list)
        hall_admins_revenue = sorted(
            award_data.hall_admin_list,
            key=lambda x: x.average_revenue,
            reverse=True
        )
        hall_admins_rating = get_categories_from_list(hall_admins_revenue)
        position = get_position_type(
            special=hookah_rating.first,
            common=hall_admins_rating.first,
            employee_id=employee_id
        )
        return Rating(
            special_rating=hookah_rating,
            common_rating=hall_admins_rating,
            position=position
        )
