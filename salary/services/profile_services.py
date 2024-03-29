import datetime
import logging
import os

from dateutil.relativedelta import relativedelta
from typing import Union, Any

from django.contrib.auth.models import User
from django.db.models import QuerySet


HOURS_VARIANT = ('час', 'часа', 'часов')
DAYS_VARIANT = ('день', 'дня', 'дней')
MONTH_VARIANT = ('месяц','месяца','месяцев')
YEARS_VARIANT = ('год', 'года', 'лет')


logger = logging.getLogger(__name__)


def profile_photo_is_exists(profile: Any) -> bool:
    """
    Return True if profile.photo is defined and image file is exists.
    """
    result = False

    try:
        result = os.path.exists(profile.photo.path)
    except ValueError:
        logger.info(f'Profile {profile.pk} has no photo.')
    except Exception as e:
        logger.debug(
            f'Unknown exception {e} in check photo profile {profile.pk}.')
    finally:
        return result


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


def get_expirience_string(
    employment_date: datetime.date,
    expiration_date: Union[datetime.date, None] = None) -> str:
    """
    Return employee comprehended expirience in day, month, year format

    Returns:
        str: comprehended employee expirience value
    """
    if expiration_date and employment_date > expiration_date:
        raise ValueError('Error in dates employment date later than'
                         ' expiration date')
    if not expiration_date:
        expiration_date = datetime.date.today()
    experience = relativedelta(expiration_date, employment_date)
    experience_values_list = [
        (experience.years, YEARS_VARIANT),
        (experience.months, MONTH_VARIANT),
        (experience.days, DAYS_VARIANT),
    ]
    experience_params_list = [
        ' '.join((str(value), get_choice_plural(value, variants)))
        for value, variants in experience_values_list
        if value
    ]
    experience_text = ' '.join(experience_params_list)
    return experience_text if experience_text else 'менее 1 дня'


def get_birthday_person_list(day: int, month: int) -> QuerySet:
    """
    Returns list of employees whose birthday is
    """
    birthday_person_list = User.objects.select_related('profile').filter(
        profile__birth_date__day=day,
        profile__birth_date__month=month,
    ).exclude(profile__profile_status='DSM')

    return birthday_person_list
