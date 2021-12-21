import datetime
from django import template

from salary.models import *


register = template.Library()

@register.simple_tag()
def total_sum(*args):
    return sum(args)

@register.simple_tag()
def date_format(date):
    return date.strftime('%d.%m.%Y')