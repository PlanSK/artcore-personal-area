from django.contrib.auth.models import User
from django.db.models import QuerySet
from typing import NamedTuple

from salary.models import WorkingShift
from salary.services.earnings import Earnings


class EmployeeData(NamedTuple):
    employee: User
    shift_counter: int
    revenue: list
    earnings: float
    shortage: float
    penalty: float


class MonthlyData(NamedTuple):
    employees: list[EmployeeData]
    shift_counter: int
    monthly_summary_revenue: float
    summary_all_earnings: float
    summary_all_shortages: float
    summary_all_penalties: float


def get_employee_data(employee: User,
                      earnings_data: Earnings) -> EmployeeData:
    revenue = []
    earnings = earnings_data.estimated_earnings
    shortage = earnings_data.shortage
    penalty = earnings_data.penalty
    return EmployeeData(employee=employee, shift_counter=1, revenue=revenue,
                        earnings=earnings, shortage=shortage, penalty=penalty)


def analyze_workshift_data(workshifts: QuerySet) -> MonthlyData:
    employee_data_dict: dict = {}
    counter = 0
    monthly_summary_revenue = 0.0
    for workshift in workshifts:
        counter += 1
        monthly_summary_revenue += workshift.summary_revenue
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
                    data['revenue'].append(workshift.summary_revenue)
                    data['earnings'].append(employee_data.earnings)
                    data['shortage'].append(employee_data.shortage)
                    data['penalty'].append(employee_data.penalty)
                else:
                    employee_data_dict[employee_data.employee] = {
                        'revenue': [workshift.summary_revenue],
                        'earnings': [employee_data.earnings],
                        'shortage': [employee_data.shortage],
                        'penalty': [employee_data.penalty]
                    }
    employee_data_list = [
        EmployeeData(
            employee=employee,
            shift_counter=len(employee_data_dict[employee].get('earnings')),
            revenue=round(
                sum(employee_data_dict[employee].get('revenue')), 2
            ),
            earnings=round(
                sum(employee_data_dict[employee].get('earnings')), 2
            ),
            shortage=round(
                sum(employee_data_dict[employee].get('shortage')), 2
            ),
            penalty=round(sum(employee_data_dict[employee].get('penalty')), 2)
        ) for employee in employee_data_dict.keys()
        ]
    employee_data_list.sort(key=lambda x: x.revenue, reverse=True)
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
        monthly_summary_revenue=round(monthly_summary_revenue, 2),
        summary_all_earnings=round(summary_earnings, 2),
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
