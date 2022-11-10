import datetime

from unidecode import unidecode

from django.utils.text import slugify


def get_misconduct_slug(last_name: str, date: datetime.date):
    return slugify(f'{unidecode(last_name)} {date.strftime("%d %m %Y")}')
