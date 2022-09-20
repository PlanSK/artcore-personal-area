import logging
from unidecode import unidecode
from collections import namedtuple

from django.utils.text import slugify

from .config import *
from salary.models import *


logger = logging.getLogger(__name__)


def get_misconduct_slug(last_name, date):
    return slugify(f'{unidecode(last_name)} {date.strftime("%d %m %Y")}')


def get_choice_plural(amount: int, variants: tuple) -> str:
    """Возвращает слово во множественном числе, в зависимости от числа

    Args:
        amount (int): число
        variants (tuple): набор вариантов слов во множественном числе

    Returns:
        str: слово из набора во множественном числе
    """

    if amount % 10 == 1 and amount % 100 != 11:
        choice = 0
    elif amount % 10 >= 2 and amount % 10 <= 4 and \
            (amount % 100 < 10 or amount % 100 >= 20):
        choice = 1
    else:
        choice = 2

    return variants[choice]

Intruder = namedtuple('Intruder', 'employee total_count explanation_count decision_count')
