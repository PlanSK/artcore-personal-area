from django.contrib.auth.models import User
from django.db.models import QuerySet
from typing import NamedTuple

from salary.models import WorkingShift
from salary.services.earnings import Earnings


class EmployeeData(NamedTuple):
    employee: User
    shift_counter: int
    earnings: float
    shortage: float
    penalty: float


class MonthlyData(NamedTuple):
    employees: list[EmployeeData]
    shift_counter: int
    summary_all_earnings: float
    summary_all_shortages: float
    summary_all_penalties: float


def get_monthly_workshift(month: int, year: int) -> QuerySet:
    queryset = WorkingShift.objects.select_related(
        'cash_admin__profile__position',
        'hall_admin__profile__position',
    ).filter(
        shift_date__month=month,
        shift_date__year=year,
        is_verified=True
    )
    return queryset


def get_employee_data(employee: User,
                      earnings_data: Earnings) -> EmployeeData:
    earnings = earnings_data.estimated_earnings
    shortage = earnings_data.shortage
    penalty = earnings_data.penalty
    return EmployeeData(employee=employee, shift_counter=1,
                        earnings=earnings, shortage=shortage, penalty=penalty)


def analyze_workshift_data(workshifts: QuerySet):
    employee_data_dict: dict = {}
    counter = 0
    for workshift in workshifts:
        counter += 1
        cashier_earnings_data = get_employee_data(
            workshift.cash_admin, workshift.cashier_earnings
        )
        hall_admin_earnings_data = get_employee_data(
            workshift.hall_admin, workshift.hall_admin_earnings
        )
        for employee_data in (hall_admin_earnings_data, cashier_earnings_data):
            if employee_data_dict.get(employee_data.employee):
                data = employee_data_dict[employee_data.employee]
                data['earnings'].append(employee_data.earnings)
                data['shortage'].append(employee_data.shortage)
                data['penalty'].append(employee_data.penalty)
            else:
                employee_data_dict[employee_data.employee] = {
                    'earnings': [employee_data.earnings],
                    'shortage': [employee_data.shortage],
                    'penalty': [employee_data.penalty]
                }
    employee_data_list = [
        EmployeeData(
            employee=employee,
            shift_counter=len(employee_data_dict[employee].get('earnings')),
            earnings=sum(employee_data_dict[employee].get('earnings')),
            shortage=sum(employee_data_dict[employee].get('shortage')),
            penalty=sum(employee_data_dict[employee].get('penalty'))
        ) for employee in employee_data_dict.keys()
        ]
    summary_earnings = 0.0
    summary_shortages = 0.0
    summary_penalties = 0.0
    for employee in employee_data_list:
        summary_earnings += employee.earnings
        summary_shortages += employee.shortage
        summary_penalties += employee.penalty
    
    return MonthlyData(
        employees=employee_data_list,
        shift_counter=counter,
        summary_all_earnings=summary_earnings,
        summary_all_shortages=summary_shortages,
        summary_all_penalties=summary_penalties
    )
