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
    count: int
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
        count=misconducts_from_db.count(),
        wait_explanation=wait_explanation,
        penalty_sum=penalty_sum
    )
