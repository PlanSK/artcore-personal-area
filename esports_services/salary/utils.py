from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.text import slugify

from unidecode import unidecode
from typing import *

from salary.models import Misconduct


class TotalDataMixin:
    def get_total_values(self, request_user, workshifts):
        position = request_user.profile.position.name
        summary_bar_revenue = 0.0
        summary_game_zone_revenue = 0.0
        summary_vr_revenue = 0.0
        total_revenue = 0.0
        summary_earnings = 0.0
        summary_error = 0.0
        summary_shortage = 0.0
        summary_hookah = 0.0

        for get_shift in workshifts:
            summary_bar_revenue += get_shift.bar_revenue
            summary_game_zone_revenue += get_shift.game_zone_revenue
            summary_vr_revenue += get_shift.vr_revenue
            summary_hookah += get_shift.hookah_revenue
            total_revenue += get_shift.get_summary_revenue()
            summary_error += get_shift.game_zone_error
            if not get_shift.shortage_paid:
                summary_shortage += get_shift.shortage
            if get_shift.is_verified:
                if position == 'hall_admin':
                    summary_earnings += get_shift.hall_admin_earnings_calc()['final_earnings']
                elif position == 'cash_admin':
                    summary_earnings += get_shift.cashier_earnings_calc()['final_earnings']

        quantity_shifts = len(workshifts)
        if len(workshifts):
            average_revenue = round(total_revenue / quantity_shifts)
        else:
            average_revenue = 0.0

        returned_dict = {
            'bar': summary_bar_revenue,
            'game_zone': summary_game_zone_revenue,
            'game_zone_error': summary_error,
            'vr': summary_vr_revenue,
            'hookah': summary_hookah,
            'sum_revenue': total_revenue,
            'quantity_shifts': quantity_shifts,
            'average_revenue': average_revenue,
            'summary_shortage': summary_shortage,
            'summary_earnings': summary_earnings,
        }
        return returned_dict


class StaffPermissionRequiredMixin(PermissionRequiredMixin):
    permission_required = (
        'auth.add_user',
        'auth.change_user',
        'auth.view_user',
        'salary.add_profile',
        'salary.change_profile',
        'salary.view_profile',
        'salary.view_workingshift',
        'salary.add_workingshift',
        'salary.change_workingshift',
        'salary.delete_workingshift',
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
