import datetime
import logging

from dataclasses import dataclass
from enum import Enum

from calendar import monthrange
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Avg, QuerySet
from django.http import Http404

from salary.models import WorkingShift


logger = logging.getLogger(__name__)


class StatusField(Enum):
    DECLINE = 0
    RISE = 1
    EQUAL = 2


@dataclass
class AnalyticField:
    name: str
    previous_month_value: float
    current_month_value: float
    ratio: float
    status: StatusField
    is_negative: bool = False


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
    """Returns AnalyticField with reсeived data"""

    negative_fields_tuple = ('shortage', 'game_zone_error')

    if previous_month_value == 0:
        ratio = -1
    else:
        ratio = (
            previous_month_value - current_month_value) / previous_month_value

    if previous_month_value == current_month_value:
        status = StatusField.EQUAL
    elif previous_month_value > current_month_value:
        status = StatusField.DECLINE
    else:
        status = StatusField.RISE
    is_negative = True if field_name in negative_fields_tuple else False

    return AnalyticField(
        name=WorkingShift._meta.get_field(field_name).verbose_name,
        previous_month_value=round(previous_month_value, 2),
        current_month_value=round(current_month_value, 2),
        ratio=round(abs(ratio * 100), 2),
        status=status,
        is_negative=is_negative
    )


def _get_peak_workshift_model(workshift: WorkingShift) -> PeakWorkshift:
    """Return PeakWorkshift from WorkingShift model data"""
    return PeakWorkshift(
        summary_revenue=workshift.summary_revenue,
        shift_date=workshift.shift_date,
        hall_admin_name=workshift.hall_admin.get_full_name(),
        cash_admin_name=workshift.cash_admin.get_full_name(),
    )


def get_peak_workshifts_data(current_month_queryset: QuerySet,
                             criteria_field: str) -> tuple[PeakWorkshift]:
    """Returns maximal and minimal PeakWorkshift by criteria field"""
    summary_revenue_sorted_queryset = current_month_queryset.order_by(
        criteria_field)

    max_revenue_workshift_data = _get_peak_workshift_model(
        summary_revenue_sorted_queryset.last()
    )
    min_revenue_workshift_data = _get_peak_workshift_model(
        summary_revenue_sorted_queryset.first()
    )
    return (max_revenue_workshift_data, min_revenue_workshift_data)


def get_last_day_date_of_previous_month(
        current_period_date: datetime.date) -> datetime.date:
    """
    Returns date of day previous month for a current date last day
    number
    """
    previous_month_date = datetime.date(
        current_period_date.year, current_period_date.month, 1
        ) - relativedelta(months=1)
    _, previous_date_limit_day_number = monthrange(
        previous_month_date.year, previous_month_date.month)
    limited_day_number = previous_date_limit_day_number

    if previous_date_limit_day_number > current_period_date.day:
        limited_day_number = current_period_date.day

    return datetime.date(previous_month_date.year,
                         previous_month_date.month,
                         limited_day_number)


def get_querysets_for_specific_period(
        year: int, month: int) -> tuple[QuerySet, QuerySet]:
    """
    Returns Queryset data for a specific period
    (previous and current months limited by day number)
    """
    current_month_queryset = _get_workshift_data(month, year)
    try:
        last_day_of_current_month = current_month_queryset.last().shift_date
    except AttributeError:
        logger.error("QuerySet with last() has no attribute 'shift_date'")
        raise Http404

    previous_period_date = get_last_day_date_of_previous_month(
        last_day_of_current_month)
    previous_month_queryset = _get_workshift_data(
        previous_period_date.month,
        previous_period_date.year,
        previous_period_date.day
    )
    current_month_limited_queryset = current_month_queryset
    if previous_period_date.day < last_day_of_current_month.day:
        current_month_limited_queryset = current_month_queryset.filter(
            shift_date__day__lte=previous_period_date.day)

    if not current_month_limited_queryset or not previous_month_queryset:
        logger.warning('QuerySets for analytic has empty result. Raise 404.')
        raise Http404

    return (current_month_limited_queryset, previous_month_queryset)


def get_analytic_data(month: int, year: int) -> AnalyticData:
    """Returns Analytic data for month and year"""
    only_summary_values_needs_fields = (
        'bar_revenue', 'game_zone_subtotal', 'game_zone_error',
        'additional_services_revenue', 'hookah_revenue', 'shortage',
        'acquiring_evator_sum', 'acquiring_terminal_sum'
    )
    total_value_needs_field = 'summary_revenue'
    summary_field_data_list = []

    (current_month_queryset,
     previous_month_queryset) = get_querysets_for_specific_period(year, month)

    total_needs_operations = [
        Avg(total_value_needs_field), Sum(total_value_needs_field)
    ]
    operation_list = [
        Sum(field_name) for field_name in only_summary_values_needs_fields
    ]
    operation_list.extend(total_needs_operations)
    current_month_data = current_month_queryset.aggregate(*operation_list)
    previous_month_data = previous_month_queryset.aggregate(*operation_list)

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

    max_revenue_data, min_revenue_data = get_peak_workshifts_data(
        current_month_queryset, total_value_needs_field
    )

    previous_month_last_day_date = previous_month_queryset.last().shift_date
    current_month_last_day_date = current_month_queryset.last().shift_date

    return AnalyticData(
        previous_period_date=previous_month_last_day_date,
        current_period_date=current_month_last_day_date,
        summary_fields_list=summary_field_data_list,
        summary_revenue_data=summary_revenue_data,
        avg_revenue_data=avg_revenue_data,
        max_revenue_workshift_data=max_revenue_data,
        min_revenue_workshift_data=min_revenue_data
    )


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