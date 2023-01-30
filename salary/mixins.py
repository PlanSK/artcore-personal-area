import datetime
import logging
from typing import Any

from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect, render
from django.views.generic.base import View

from .models import *
from salary.services.utils import logging_exception


logger = logging.getLogger(__name__)


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


class EditModelEditorFieldsMixin:
    def form_valid(self, form):
        self.object.editor = self.request.user.get_full_name()
        return super().form_valid(form)


class ProfileStatusRedirectMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.profile.profile_status == Profile.ProfileStatus.WAIT:
                return redirect('pending_verification')
            elif (request.user.profile.profile_status == Profile.ProfileStatus.REGISTRED or
                    request.user.profile.profile_status == Profile.ProfileStatus.DISMISSED):
                return self.handle_no_permission()
        else:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class MonthYearExtractMixin:
    def dispatch(self, request: HttpRequest, *args: Any,
                 **kwargs: Any) -> HttpResponse:
        month, year = datetime.date.today().month, datetime.date.today().year
        self.month = kwargs.get('month') if kwargs.get('month') else month
        self.year = kwargs.get('year') if kwargs.get('year') else year
        return super().dispatch(request, *args, **kwargs)


class CatchingExceptionsMixin(View):
    def dispatch(self, request: HttpRequest, *args: Any,
                 **kwargs: Any) -> HttpResponse:
        try:
            response = super().dispatch(request, *args, **kwargs)
        except Exception as exception_instance:
            # there might be an error handler here or redirection to correct page
            logging_exception(request, exception_instance)
            raise
        else:
            return response
