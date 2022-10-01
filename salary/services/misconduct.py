import logging
from typing import NamedTuple
from unidecode import unidecode

from django.utils.text import slugify
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class Intruder(NamedTuple):
    employee: User
    total_count: int
    explanation_count: int
    decision_count: int


def get_misconduct_slug(last_name, date):
    return slugify(f'{unidecode(last_name)} {date.strftime("%d %m %Y")}')
