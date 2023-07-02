import datetime
import logging

from dataclasses import dataclass
from enum import Enum

from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Avg, QuerySet

from salary.models import WorkingShift


logger = logging.getLogger(__name__)


class StatusField(Enum):
    DECLINE = 0
    RISE = 1


@dataclass
class AnalyticField:
    name: str
    previous_month_value: float
    current_month_value: float
    ratio: float
    status: StatusField


@dataclass
class PeakWorkshift:
    summary_revenue: float
    shift_date: datetime.date
    hall_admin_name: str
    cash_admin_name: str


@dataclass
class AnalyticData:
    previous_period_date: datetime.date
    current_period_date: datetime.date
    summary_fields_list: list[AnalyticField]
    summary_revenue_data: AnalyticField
    avg_revenue_data: AnalyticField
    max_revenue_workshift_data: PeakWorkshift
    min_revenue_workshift_data: PeakWorkshift


def _get_workshift_data(month: int, year: int, day: int = 0) -> QuerySet:
    """Returns queryset with workshifts sorted by date"""
    queryset = WorkingShift.objects.all().select_related(
        'hall_admin', 'cash_admin').filter(
            shift_date__year=year,
            shift_date__month=month).order_by('shift_date')
    if day:
        return queryset.filter(shift_date__day__lte=day)

    return queryset


def _get_analytic_field(current_month_value: float,
                       previous_month_value: float,
                       field_name: str) -> AnalyticField:
    ratio = previous_month_value * 100 / current_month_value - 100
    status = StatusField.DECLINE if ratio > 0 else StatusField.RISE
    return AnalyticField(
        name=WorkingShift._meta.get_field(field_name).verbose_name,
        previous_month_value=previous_month_value,
        current_month_value=current_month_value,
        ratio=round(abs(ratio), 2),
        status=status
    )


def get_analytic_data(month: int, year: int) -> AnalyticData:
    try:
        current_month_date = datetime.date(year, month, 1)
    except ValueError:
        logger.error('Error convert month and year to correct date')
        raise ValueError('Incorrent month or year')
    previous_month_date = current_month_date - relativedelta(months=1)
    current_month_queryset = _get_workshift_data(month, year)
    limited_day_number = current_month_queryset.last().shift_date.day
    previous_month_queryset = _get_workshift_data(previous_month_date.month,
                                                  previous_month_date.year,
                                                  limited_day_number)

    only_summary_values_needs_fields = (
        'bar_revenue', 'game_zone_subtotal', 'game_zone_error',
        'additional_services_revenue', 'hookah_revenue', 'shortage',
        'acquiring_evator_sum', 'acquiring_terminal_sum'
    )
    total_value_needs_field = 'summary_revenue'
    total_needs_operations = [
        Avg(total_value_needs_field), Sum(total_value_needs_field)
    ]

    operation_list = [
        Sum(field_name) for field_name in only_summary_values_needs_fields
    ]
    operation_list.extend(total_needs_operations)

    current_month_data = current_month_queryset.aggregate(*operation_list)
    previous_month_data = previous_month_queryset.aggregate(*operation_list)

    summary_field_data_list = []
    for field, value in current_month_data.items():
        field_name, value_type = field.split('__')
        analytic_field = _get_analytic_field(round(value, 2),
                                             previous_month_data.get(field, 0),
                                             field_name)
        if total_value_needs_field in field and value_type == 'avg':
            avg_revenue_data = analytic_field
        elif total_value_needs_field in field and value_type == 'sum':
            summary_revenue_data = analytic_field
        else:
            summary_field_data_list.append(analytic_field)
    summary_revenue_sorted_queryset = current_month_queryset.order_by(
        total_value_needs_field)
    max_revenue_workshift = summary_revenue_sorted_queryset.last()
    min_revenue_workshift = summary_revenue_sorted_queryset.first()
    max_revenue_workshift_data = PeakWorkshift(
        summary_revenue=max_revenue_workshift.summary_revenue,
        shift_date=max_revenue_workshift.shift_date,
        hall_admin_name=max_revenue_workshift.hall_admin.get_full_name(),
        cash_admin_name=max_revenue_workshift.cash_admin.get_full_name(),
    )
    min_revenue_workshift_data = PeakWorkshift(
        summary_revenue=min_revenue_workshift.summary_revenue,
        shift_date=min_revenue_workshift.shift_date,
        hall_admin_name=min_revenue_workshift.hall_admin.get_full_name(),
        cash_admin_name=min_revenue_workshift.cash_admin.get_full_name(),
    )
    return AnalyticData(
        previous_period_date=datetime.date(previous_month_date.year,
                                           previous_month_date.month,
                                           limited_day_number),
        current_period_date=datetime.date(year, month, limited_day_number),
        summary_fields_list=summary_field_data_list,
        summary_revenue_data=summary_revenue_data,
        avg_revenue_data=avg_revenue_data,
        max_revenue_workshift_data=max_revenue_workshift_data,
        min_revenue_workshift_data=min_revenue_workshift_data
    )


# class MonthlyAnaliticData:
#     def get_fields_dict(self) -> dict:
#         fields = (
#             'summary_revenue', 'bar_revenue', 'game_zone_subtotal',
#             'game_zone_error', 'additional_services_revenue', 'hookah_revenue',
#             'shortage', 'summary_revenue__avg',
#         )
#         self.current_month_queryset = self.object_list.filter(
#             shift_date__month=self.month,
#             shift_date__year=self.year,
#         )

#         # if not self.current_month_queryset:
#         #     raise Http404

#         self.current_date = datetime.date(self.year, self.month, 1)

#         self.previous_month_date = self.current_date - relativedelta(months=1)
#         self.previous_month_queryset = self.object_list.filter(
#             shift_date__month=self.previous_month_date.month,
#             shift_date__year=self.previous_month_date.year,
#         )

#         values_dict = dict()
#         operations_list = [
#             Sum(field) if '__avg' not in field
#             else Avg(field.split('__')[0])
#             for field in fields
#         ]

#         current_month_values = self.current_month_queryset.aggregate(*operations_list)
#         previous_month_values = self.previous_month_queryset.aggregate(*operations_list)

#         for field in current_month_values.keys():
#             current_month_value = round(current_month_values.get(field, 0), 2)
#             previous_month_value = round(
#                 previous_month_values.get(field, 0), 2
#             ) if previous_month_values.get(field, 0) else 0

#             if current_month_value == 0.0:
#                 ratio = 100.0
#             elif current_month_value > previous_month_value:
#                 ratio = round((current_month_value - previous_month_value) /
#                             current_month_value * 100, 2)
#             elif current_month_value < previous_month_value:
#                 ratio = round((previous_month_value - current_month_value) /
#                             previous_month_value * 100, 2)

#             values_dict[field] = (
#                         previous_month_value,
#                         current_month_value,
#                         ratio,
#                     )

#         return values_dict

#     def get_linechart_data(self) -> list:
#         """Return list of lists with revenue data for Google LineChart

#         Returns:
#             list: list of lists [day_of_month, previous_month_revenue, current_month_revenue]
#         """
#         current_month_list =  self.current_month_queryset.values_list(
#             'shift_date__day',
#             'summary_revenue')
#         previous_month_list = self.previous_month_queryset.values_list(
#             'shift_date__day',
#             'summary_revenue')
#         linechart_data_list = list()
#         for first_element in previous_month_list:
#             for second_element in current_month_list:
#                 if first_element[0] == second_element[0]:
#                     data_row = list(first_element)
#                     data_row.append(second_element[1])
#                     linechart_data_list.append(data_row)

#         return linechart_data_list

#     def get_piechart_data(self, analytic_data: dict) -> list:
#         categories = {
#             'bar_revenue': 'Бар',
#             'game_zone_subtotal': 'Game zone',
#             'additional_services_revenue': 'Доп. услуги',
#             'hookah_revenue': 'Кальян',
#         }

#         piechart_data = list()

#         for category in categories.keys():
#             piechart_data.append(
#                 [categories.get(category), analytic_data.get(f'{category}__sum')[1]]
#             )

#         return piechart_data