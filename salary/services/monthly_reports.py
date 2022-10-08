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
    average_gamezone_revenue: float
    summary_bar_revenue: float
    summary_hookah_revenue: float


class MonthlyData(NamedTuple):
    employees: list[EmployeeData]
    shift_counter: int
    summary_basic_revenue: float
    summary_bonus_revenue: float
    summary_all_shortages: float
    summary_all_penalties: float


def get_employee_data(employee: User,
                      earnings_data: Earnings) -> EmployeeData:
    return EmployeeData(
        employee=employee,
        shift_counter=1,
        basic_revenues=earnings_data.basic_part.summary,
        bonus_revenues=earnings_data.bonus_part.summary,
        shortage=earnings_data.shortage,
        penalty=earnings_data.penalty,
        average_gamezone_revenue=0.0,
        summary_bar_revenue=0.0,
        summary_hookah_revenue=0.0,
    )


def analyze_workshift_data(workshifts: QuerySet) -> MonthlyData:
    employee_data_dict: dict = {}
    all_workshifts_counter = 0

    for workshift in workshifts:
        all_workshifts_counter += 1
        cashier_earnings_data = get_employee_data(
            workshift.cash_admin, workshift.cashier_earnings
        )
        hall_admin_earnings_data = get_employee_data(
            workshift.hall_admin, workshift.hall_admin_earnings
        )

        for employee_data in (hall_admin_earnings_data, cashier_earnings_data):
            if employee_data.employee.profile.position.position_salary:
                if employee_data_dict.get(employee_data.employee):
                    data = employee_data_dict[employee_data.employee]
                    data['basic_part'].append(employee_data.basic_revenues)
                    data['bonus_part'].append(employee_data.bonus_revenues)
                    data['shortage'].append(employee_data.shortage)
                    data['penalty'].append(employee_data.penalty)
                    data['game_zone_revenues'].append(
                        workshift.game_zone_subtotal
                    )
                    data['bar_revenues'].append(workshift.bar_revenue)
                    data['hookah_revenues'].append(workshift.hookah_revenue)
                else:
                    employee_data_dict[employee_data.employee] = {
                        'basic_part': [employee_data.basic_revenues],
                        'bonus_part': [employee_data.bonus_revenues],
                        'shortage': [employee_data.shortage],
                        'penalty': [employee_data.penalty],
                        'game_zone_revenues': [workshift.game_zone_subtotal],
                        'bar_revenues': [workshift.bar_revenue],
                        'hookah_revenues': [workshift.hookah_revenue],
                    }
    employee_data_list = []
    for employee in employee_data_dict.keys():
        employee_shift_counter = len(
            employee_data_dict[employee].get('basic_part')
        )
        summary_game_zone_revenues = sum(
            employee_data_dict[employee].get('game_zone_revenues')
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
            average_gamezone_revenue=round(
                summary_game_zone_revenues / employee_shift_counter, 2
            ),
            summary_bar_revenue=round(
                sum(employee_data_dict[employee].get('bar_revenues')), 2
            ),
            summary_hookah_revenue=round(
                sum(employee_data_dict[employee].get('bar_revenues')), 2
            ),
        )
        employee_data_list.append(current_employee_data)

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
        shift_counter=all_workshifts_counter,
        summary_basic_revenue=round(monthly_summary_basic_part, 2),
        summary_bonus_revenue=round(monthly_summary_bonus_part, 2),
        summary_all_shortages=round(summary_shortages, 2),
        summary_all_penalties=round(summary_penalties, 2)
    )


def get_monthly_report(month: int, year: int) -> MonthlyData:
    workshifts = WorkingShift.objects.select_related(
        'cash_admin__profile__position',
        'hall_admin__profile__position',
    ).filter(
        shift_date__month=month,
        shift_date__year=year,
        is_verified=True
    )
    return analyze_workshift_data(workshifts)
