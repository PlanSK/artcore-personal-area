from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.db.models import Q

from .forms import *

import datetime
from dateutil.relativedelta import relativedelta


def registration(request):
    if request.method == 'POST':
        user_form = UserRegistration(request.POST)
        profile_form = EmployeeRegistration(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.is_active = False
            user.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            return redirect('login')
    else:
        form = UserRegistration()
        employee_form = EmployeeRegistration()
    context = {
        'title': 'Регистрация сотрудника',
        'form': form,
        'employee_form': employee_form
    }
    return render(request, 'salary/registration.html', context=context)


class LoginUser(LoginView):
    template_name = 'salary/login.html'
    form_class = AuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Авторизация'
        return context

    def get_success_url(self, **kwargs):
        return reverse_lazy('index')


class IndexView(LoginRequiredMixin, TemplateView):
    login_url = 'login/'
    template_name = 'salary/account.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Личный кабинет'

        current_year = self.kwargs.get('year', datetime.date.today().year)
        current_month = self.kwargs.get('month', datetime.date.today().month)

        previous_date = datetime.date(current_year, current_month, 1) - relativedelta(months=1)
        next_date = datetime.date(current_year, current_month, 1) + relativedelta(months=1)
        if self.get_user_workshifts(month=previous_date.month, year=previous_date.year):
            context['previous_date'] = previous_date
        if self.get_user_workshifts(month=next_date.month, year=next_date.year):
            context['next_date'] = next_date

        context['current_date'] = datetime.date(current_year, current_month, 1)
        context['experience'] = self.get_work_experience()
        context['tables'] = self.get_user_workshifts(month=current_month, year=current_year)
        context['total_values'] = self.get_total_values(context['tables'])
        context['current_workshift'] = self.get_current_shift()

        return context

    def get_user_workshifts(self, month, year):
        workshifts = WorkingShift.objects.filter(
            shift_date__year=year,
            shift_date__month=month
        ).filter(Q(cash_admin=self.request.user) | Q(hall_admin=self.request.user)).order_by('-shift_date')

        if not workshifts:
            return []

        for get_shift in workshifts:
            get_shift.kpi_salary = self.kpi_salary_calculate(get_shift)

        return workshifts

    def kpi_salary_calculate(self, workshift) -> float:
        if not workshift.is_verified:
            return 0.0
        current_user = self.request.user
        kpi_criteria = {
            'hall_admin': {
                'bar' : [(0, 0.005), (3000, 0.01), (4000, 0.02), (6000, 0.025), (8000, 0.03)],
                'game_zone':[(0, 0.005), (20000, 0.01), (25000, 0.0125), (27500, 0.015), (30000, 0.0175)],
                'vr': [(0, 0.1), (1000, 0.12), (2000, 0.13), (3000, 0.14), (5000, 0.15)]
            },
            'cash_admin': {
                'bar' : [(0, 0.03), (3000, 0.04), (4000, 0.05), (6000, 0.06), (8000, 0.07)],
                'game_zone':[(0, 0.005), (20000, 0.01), (25000, 0.0125), (27500, 0.015), (30000, 0.0175)],
                'vr': [(0, 0.05), (1000, 0.06), (2000, 0.065), (3000, 0.07), (5000, 0.075)]
            }
        }
        experience_bonus = 200
        hall_cleaning_bonus = 400
        attestation_bonus = 200
        discipline_bonus = 1000

        if current_user.profile.position.name == 'hall_admin':
            kpi_ratio = kpi_criteria['hall_admin']
            discipline = workshift.hall_admin_discipline
            hall_cleaning = workshift.hall_cleaning
        elif current_user.profile.position.name == 'cash_admin':
            kpi_ratio = kpi_criteria['cash_admin']
            hall_cleaning = False
            discipline = workshift.cash_admin_discipline
        else:
            raise ValueError('Position settings is not defined.')

        revenue_list = [
            (workshift.bar_revenue, kpi_ratio['bar']),
            (workshift.game_zone_revenue - workshift.game_zone_error, kpi_ratio['game_zone']),
            (workshift.vr_revenue, kpi_ratio['vr'])
        ]

        # Position salary
        shift_salary = current_user.profile.position.position_salary

        # Expirience calc
        experience = (datetime.date.today() - current_user.profile.employment_date).days
        if experience > 90:
            shift_salary += experience_bonus

        # Discipline
        if discipline:
            shift_salary += discipline_bonus

        # Hall cleaning
        if hall_cleaning:
            shift_salary += hall_cleaning_bonus
        
        # Attestation
        if current_user.profile.attestation_date and current_user.profile.attestation_date <= workshift.shift_date:
            shift_salary += attestation_bonus

        # KPI
        for current_revenue, ratio_list in revenue_list:
            for revenue_value, ratio in ratio_list:
                if current_revenue >= revenue_value:
                    bonus = current_revenue * ratio
            shift_salary += bonus

        if current_user.profile.position.name == 'cash_admin':
            if workshift.shortage and workshift.shortage * 2 > shift_salary:
                return 0.0
            else:
                return round(shift_salary - workshift.shortage * 2, 2)
        else:
            return round(shift_salary, 2)

    def get_total_values(self, workshifts):
        summary_bar_revenue = 0.0
        summary_game_zone_revenue = 0.0
        summary_vr_revenue = 0.0
        total_revenue = 0.0
        total_salary = 0.0
        total_discipline = 0
        total_cleaning = 0
        summary_error = 0.0
        summary_shortage = 0.0
        position = self.request.user.profile.position.name

        for get_shift in workshifts:
            summary_bar_revenue += get_shift.bar_revenue
            summary_game_zone_revenue += get_shift.game_zone_revenue
            summary_vr_revenue += get_shift.vr_revenue
            total_revenue += get_shift.get_summary_revenue()
            summary_error += get_shift.game_zone_error
            summary_shortage += get_shift.shortage
            total_salary += get_shift.kpi_salary

            if position == 'hall_admin':
                if get_shift.hall_admin_discipline:
                    total_discipline += 1
                if get_shift.hall_cleaning:
                    total_cleaning += 1
            elif position == 'cash_admin' and get_shift.cash_admin_discipline:
                    total_discipline += 1

        quantity_shifts = len(workshifts)
        if len(workshifts):
            total_discipline = int(round(total_discipline / len(workshifts), 2) * 100)
            total_cleaning = int(round(total_cleaning / len(workshifts), 2) * 100)
            average_revenue = round(total_revenue / quantity_shifts)
        else:
            average_revenue = 0.0

        returned_dict = {
            'bar': summary_bar_revenue,
            'game_zone': summary_game_zone_revenue,
            'game_zone_error': summary_error,
            'vr': summary_vr_revenue,
            'sum_revenue': total_revenue,
            'quantity_shifts': quantity_shifts,
            'average_revenue': average_revenue,
            'summary_shortage': summary_shortage,
            'total_salary': total_salary,
            'total_cleaning': total_cleaning,
            'total_discipline': total_discipline
        }
        return returned_dict


    def get_current_shift(self):
        if WorkingShift.objects.filter(shift_date=datetime.date.today()):
            return WorkingShift.objects.get(shift_date=datetime.date.today())

        return None

    def get_work_experience(self):
        employment_date = User.objects.get(username=self.request.user).profile.employment_date
        
        experience = datetime.date.today() - employment_date
        days = experience.days
        experience_text = ''

        if days > 365:
            years = days // 365
            days = days % 365
            experience_text = str(years)

            if years == 1:
                experience_text += ' год '
            elif 1 < years < 5:
                experience_text += ' года '
            else:
                experience_text += ' лет '

        if days > 30:
            month = days // 30
            days = days % 30
            experience_text += str(month) + ' месяц'

            if month == 1:
                experience_text += ' '
            elif 1 < month < 5:
                experience_text += 'а '
            else:
                experience_text += 'ев '

        experience_text += str(days) + ' д'

        if 12 <= days < 15:
            experience_text += 'ней'
        else:
            end_num = days % 10

            if end_num == 1:
                experience_text += 'ень'
            elif 1 < end_num < 5:
                experience_text += 'ня'
            else:
                experience_text += 'ней'

        return experience_text

    def get_success_url(self, **kwargs):
        return reverse_lazy('index')


def logout_user(request):
    logout(request)
    return redirect('login')


class AddWorkshiftData(LoginRequiredMixin, CreateView):
    form_class = AddWorkshiftDataForm
    template_name = 'salary/add_workshift.html'
    success_url = reverse_lazy('index')

    def get_initial(self):
        initional = super().get_initial()
        initional['cash_admin'] = self.request.user
        initional['shift_date'] = datetime.date.today().strftime('%Y-%m-%d')
        return initional

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add workshift'
        return context


class EditWorkshiftData(LoginRequiredMixin, UpdateView):
    model = WorkingShift
    form_class = EditWorkshiftDataForm
    template_name = 'salary/edit_workshift.html'
    success_url = reverse_lazy('index')


class StaffEditWorkshift(LoginRequiredMixin, UpdateView):
    model = WorkingShift
    form_class = StaffEditWorkshiftForm
    template_name = 'salary/edit_workshift.html'
    success_url = reverse_lazy('index')


class DeleteWorkshift(LoginRequiredMixin, DeleteView):
    model = WorkingShift
    success_url = reverse_lazy('index')


def page_not_found(request, exception):
    response = render(request, 'salary/404.html', {'title': 'Page not found'})
    response.status_code = 404
    return response


def page_forbidden(request, exception):
    response = render(request, 'salary/403.html', {'title': 'Access forbidden'})
    response.status_code = 403
    return response