from django.contrib.auth.models import User
from django.db.models import QuerySet
from typing import NamedTuple

from salary.models import WorkingShift
from salary.services.earnings import Earnings


class EmployeeData(NamedTuple):
    employee: User
    shift_counter: int
    basic_revenues: float
    bonus_revenues: float
    shortage: float
    penalty: float
    average_revenue: float
    summary_bar_revenue: float
    summary_hookah_revenue: float


class EmployeeCategories(NamedTuple):
    cashier_list: list
    hall_admin_list: list


class MonthlyData(NamedTuple):
    employees: list[EmployeeData]
    shift_counter: int
    summary_basic_revenue: float
    summary_bonus_revenue: float
    summary_all_shortages: float
    summary_all_penalties: float


class AwardData(NamedTuple):
    cashiers_list: list
    hall_admin_list: list
    max_bar_revenue_sum: float
    max_hookah_revenue_sum: float
    max_cashier_avg_revenue: float
    max_hall_admin_avg_revenue: float


def get_employee_data(employee: User,
                      earnings_data: Earnings,
                      summary_revenue: float,
                      bar_revenue: float = 0.0,
                      hookah_revenue: float = 0.0,
                      ) -> EmployeeData:
    return EmployeeData(
        employee=employee,
        shift_counter=1,
        basic_revenues=earnings_data.basic_part.summary,
        bonus_revenues=earnings_data.bonus_part.summary,
        shortage=earnings_data.shortage,
        penalty=earnings_data.penalty,
        average_revenue=summary_revenue,
        summary_bar_revenue=bar_revenue,
        summary_hookah_revenue=hookah_revenue,
    )


def get_summary_employees_list(
    employee_data_list: list[EmployeeData]) -> list[EmployeeData]:

    employee_data_dict = {}
    summary_employee_list = []

    for employee_data in employee_data_list:
        if employee_data.employee.profile.position.position_salary:
            if employee_data_dict.get(employee_data.employee):
                data = employee_data_dict[employee_data.employee]
                data['basic_part'].append(employee_data.basic_revenues)
                data['bonus_part'].append(employee_data.bonus_revenues)
                data['shortage'].append(employee_data.shortage)
                data['penalty'].append(employee_data.penalty)
                data['revenue'].append(
                    employee_data.average_revenue
                )
                data['bar_revenues'].append(employee_data.summary_bar_revenue)
                data['hookah_revenues'].append(
                    employee_data.summary_hookah_revenue
                )
            else:
                employee_data_dict[employee_data.employee] = {
                    'basic_part': [employee_data.basic_revenues],
                    'bonus_part': [employee_data.bonus_revenues],
                    'shortage': [employee_data.shortage],
                    'penalty': [employee_data.penalty],
                    'revenue': [
                        employee_data.average_revenue
                    ],
                    'bar_revenues': [employee_data.summary_bar_revenue],
                    'hookah_revenues': [employee_data.summary_hookah_revenue],
                }
    for employee in employee_data_dict.keys():
        employee_shift_counter = len(
            employee_data_dict[employee].get('basic_part')
        )
        summary_revenues = sum(
            employee_data_dict[employee].get('revenue')
        )
        current_employee_data = EmployeeData(
            employee=employee,
            shift_counter=employee_shift_counter,
            basic_revenues=round(
                sum(employee_data_dict[employee].get('basic_part')), 2
            ),
            bonus_revenues=round(
                sum(employee_data_dict[employee].get('bonus_part')), 2
            ),
            shortage=round(
                sum(employee_data_dict[employee].get('shortage')), 2
            ),
            penalty=round(sum(employee_data_dict[employee].get('penalty')), 2),
            average_revenue=round(
                summary_revenues / employee_shift_counter, 2
            ),
            summary_bar_revenue=round(
                sum(employee_data_dict[employee].get('bar_revenues')), 2
            ),
            summary_hookah_revenue=round(
                sum(employee_data_dict[employee].get('hookah_revenues')), 2
            ),
        )
        summary_employee_list.append(current_employee_data)

    return summary_employee_list


def get_employee_workshift_data_list(
        workshifts: QuerySet) -> EmployeeCategories:

    all_workshifts_counter = 0
    cashiers_list = []
    hall_admin_list = []

    for workshift in workshifts:
        all_workshifts_counter += 1
        summary_revenue = workshift.game_zone_subtotal + workshift.vr_revenue
        cashier_earnings_data = get_employee_data(
            employee=workshift.cash_admin,
            earnings_data=workshift.cashier_earnings,
            summary_revenue=summary_revenue,
            bar_revenue=workshift.bar_revenue
        )
        hall_admin_earnings_data = get_employee_data(
            employee=workshift.hall_admin,
            earnings_data=workshift.hall_admin_earnings,
            summary_revenue=summary_revenue,
            hookah_revenue=workshift.hookah_revenue
        )
        hall_admin_list.append(hall_admin_earnings_data)
        cashiers_list.append(cashier_earnings_data)
    hall_admin_data_list = get_summary_employees_list(hall_admin_list)
    cashier_data_list = get_summary_employees_list(cashiers_list)

    return EmployeeCategories(
        cashier_list=cashier_data_list,
        hall_admin_list=hall_admin_data_list
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
    bar_max_revenue = 0.0
    cash_admin_max_avg_revenue = 0.0
    for employee in filter(lambda x: x.shift_counter >= 4,
                           categories_list.cashier_list):
        if bar_max_revenue < employee.summary_bar_revenue:
            bar_max_revenue = employee.summary_bar_revenue
        if cash_admin_max_avg_revenue < employee.average_revenue:
            cash_admin_max_avg_revenue = employee.average_revenue

    hookah_max_revenue = 0.0
    hall_admin_max_avg_revenue = 0.0
    for employee in filter(lambda x: x.shift_counter >= 4,
                           categories_list.hall_admin_list):
        if hookah_max_revenue < employee.summary_hookah_revenue:
            hookah_max_revenue = employee.summary_hookah_revenue
        if hall_admin_max_avg_revenue < employee.average_revenue:
            hall_admin_max_avg_revenue = employee.average_revenue

    categories_list.cashier_list.sort(key=lambda x: x.summary_bar_revenue,
                                      reverse=True)
    categories_list.hall_admin_list.sort(
        key=lambda x: x.summary_hookah_revenue, reverse=True
    )
    return AwardData(
        cashiers_list=categories_list.cashier_list,
        hall_admin_list=categories_list.hall_admin_list,
        max_bar_revenue_sum=bar_max_revenue,
        max_hookah_revenue_sum=hookah_max_revenue,
        max_cashier_avg_revenue=cash_admin_max_avg_revenue,
        max_hall_admin_avg_revenue=hall_admin_max_avg_revenue,
    )
