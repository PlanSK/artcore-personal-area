import datetime
import logging

from typing import NamedTuple

from django.contrib.auth.models import User
from django.db.models import QuerySet, Sum

from salary.models import Misconduct


logger = logging.getLogger(__name__)


class Intruder(NamedTuple):
    employee: User
    total_count: int
    explanation_count: int
    decision_count: int


class MisconductData(NamedTuple):
    penalty_counter: int
    wait_explanation: int
    penalty_sum: float


def _get_emloyee_misconduct(employee_id: int) -> QuerySet:
        return Misconduct.objects.filter(intruder__id=employee_id)


def get_misconduct_employee_data(
    employee_id: int, month: int = datetime.date.today().month,
        year: int = datetime.date.today().month) -> MisconductData:
    """
    Returns MisconductData with values from db.
    """
    misconducts_from_db = _get_emloyee_misconduct(employee_id)
    wait_explanation = misconducts_from_db.filter(
        status=Misconduct.MisconductStatus.ADDED).count()
    penalty_sum = misconducts_from_db.filter(
        status=Misconduct.MisconductStatus.CLOSED, workshift_date__month=month,
        workshift_date__year=year).aggregate(
            Sum('penalty')).get('penalty__sum', 0.0)

    return MisconductData(
        penalty_counter=misconducts_from_db.count(),
        wait_explanation=wait_explanation,
        penalty_sum=penalty_sum
    )


def get_sorted_intruders_list(queryset: QuerySet) -> list[Intruder]:
    intruders_dict: dict[User, list] = dict()
    for misconduct in queryset:
        if intruders_dict.get(misconduct.intruder):
            intruders_dict[misconduct.intruder].append(misconduct.status)
        else:
            intruders_dict[misconduct.intruder] = [misconduct.status,]
    
    intruders_list = [
        Intruder(
            employee=intruder,
            total_count=len(intruders_dict[intruder]),
            explanation_count=len(
                list(filter(
                    lambda x: x == Misconduct.MisconductStatus.ADDED,
                    intruders_dict[intruder]
                ))
            ),
            decision_count=len(
                list(filter(
                    lambda x: x == Misconduct.MisconductStatus.WAIT,
                    intruders_dict[intruder]
                ))
            )
        ) for intruder in intruders_dict.keys()
    ]
    sorted_intruders_list = sorted(
        intruders_list, key=lambda i: i.total_count, reverse=True
    )

    return sorted_intruders_list


def get_penalty_sum(misconduct_queryset: QuerySet) -> float:
    """Returns the amount of fines for violations"""
    if misconduct_queryset.filter(status=Misconduct.MisconductStatus.CLOSED):
        return misconduct_queryset.filter(
            status=Misconduct.MisconductStatus.CLOSED,
        ).aggregate(Sum('penalty')).get('penalty__sum')
    return 0.0
