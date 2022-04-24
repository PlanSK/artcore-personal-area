from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import QuerySet

from unidecode import unidecode
from typing import *

from salary.models import Misconduct, WorkingShift


class EmployeePermissionsMixin(PermissionRequiredMixin):
    permission_required = (
        'auth.add_user',
        'auth.change_user',
        'auth.view_user',
        'salary.add_profile',
        'salary.change_profile',
        'salary.view_profile',
    )


class WorkingshiftPermissonsMixin(PermissionRequiredMixin):
    permission_required = (
        'salary.view_workingshift',
        'salary.add_workingshift',
        'salary.change_workingshift',
        'salary.delete_workingshift',
        'salary.view_workshift_report',
        'salary.advanced_change_workshift',
    )


class MisconductPermissionsMixin(PermissionRequiredMixin):
    permission_required = (
        'salary.view_misconduct',
        'salary.add_misconduct',
        'salary.change_misconduct',
        'salary.delete_misconduct',
    )


class StaffOnlyMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        return self.request.user.is_staff


class TitleMixin(object):
    title = None

    def get_title(self):
        return self.title

    def get_context_data(self, **kwargs):
        context= super(TitleMixin, self).get_context_data(**kwargs)
        context['title'] = self.get_title()
        return context


class SuccessUrlMixin:
    success_url = reverse_lazy('index')

    def get_success_url(self):
        return self.request.GET.get('next', self.success_url)


class EditModelEditorFields:
    def form_valid(self, form):
        self.object.editor = self.request.user.get_full_name()
        self.object.change_date = timezone.localtime(timezone.now())
        return super().form_valid(form)


def return_misconduct_slug(last_name, date):
    slug_name = slugify(f'{unidecode(last_name)} {date.strftime("%d %m %Y")}')
    count = Misconduct.objects.filter(slug__startswith=slug_name).count()
    if not count:
        return slug_name
    else:
        return f'{slug_name}-{count}'


def get_workshift_revenue_analyze(workshifts: QuerySet) -> tuple:
    """Return sum of 'summary_revenue' properties

    Args:
        workshifts (QuerySet): WorkingShift.objects queryset

    Returns:
        tuple: (summary_revenue, average_revenue, min_revenue, max_revenue)
    """
    revenues_list = [workshift.summary_revenue for workshift in workshifts]
    summary_revenue = sum(revenues_list)
    average_revenue = round(summary_revenue / len(revenues_list), 2)
    min_revenue = min(revenues_list)
    max_revenue = max(revenues_list)

    return (summary_revenue, average_revenue, min_revenue, max_revenue)
