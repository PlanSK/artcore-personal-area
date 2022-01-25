from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, ListView
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.db.models import Q

from .forms import *
from .utils import *

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


class StaffUserView(LoginRequiredMixin, TotalDataMixin, TemplateView):
    template_name = 'salary/staff_user_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_user = self.kwargs.get('request_user')
        get_user = get_object_or_404(User, username=request_user)
        workshifts = WorkingShift.objects.filter(
            shift_date__year=datetime.date.today().year,
            shift_date__month=datetime.date.today().month
        ).filter(Q(cash_admin=get_user) | Q(hall_admin=get_user)).order_by('-shift_date')
        context['title'] = f'Данные польователя {get_user}'
        context['request_user'] = get_user
        context['workshifts'] = workshifts
        context['total_values'] = self.get_total_values(get_user, workshifts)

        return context


class IndexView(LoginRequiredMixin, TotalDataMixin, TemplateView):
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
        context['experience'] = self.request.user.profile.get_work_experience
        context['workshifts'] = self.get_user_workshifts(month=current_month, year=current_year)
        context['total_values'] = self.get_total_values(self.request.user, context['workshifts'])
        context['current_workshift'] = self.get_current_shift()

        return context

    def get_user_workshifts(self, month, year):
        workshifts = WorkingShift.objects.filter(
            shift_date__year=year,
            shift_date__month=month
        ).filter(Q(cash_admin=self.request.user) | Q(hall_admin=self.request.user)).order_by('-shift_date')

        if not workshifts:
            return []

        return workshifts

    def get_current_shift(self):
        if WorkingShift.objects.filter(shift_date=datetime.date.today()):
            return WorkingShift.objects.get(shift_date=datetime.date.today())

        return None

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

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['start_date'] = context['object'].shift_date - relativedelta(days=1)
        return context


class DeleteWorkshift(LoginRequiredMixin, DeleteView):
    model = WorkingShift
    success_url = reverse_lazy('index')


class MonthlyReportListView(LoginRequiredMixin, ListView):
    model = WorkingShift
    template_name = 'salary/monthlyreport_list.html'

    def get_queryset(self):
        month = datetime.date.today().month
        workshifts = WorkingShift.objects.filter(shift_date__month=month, is_verified=True)
        return workshifts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hall_admin_dict = dict()
        cash_admin_dict = dict()
        # TODO: здесь подсчет смен и пользователей.
        for workshift in context['object_list']:
            kpi_hall = workshift.kpi_salary_calculate(workshift.hall_admin)
            kpi_cash = workshift.kpi_salary_calculate(workshift.cash_admin)

            if kpi_hall['penalty'] > 1000:
                hall_penalty = 1000
            else:
                hall_penalty = kpi_hall['penalty']

            if kpi_cash['penalty'] > 1000:
                cash_penalty = 1000
            else:
                cash_penalty = kpi_cash['penalty']

            final_salary_hall = kpi_hall['calculated_salary'] - hall_penalty
            final_salary_cash = kpi_cash['calculated_salary'] - cash_penalty

            hall_values_list = [
                kpi_hall['calculated_salary'], kpi_hall['penalty'],
                0, final_salary_hall
            ]

            cash_values_list = [
                kpi_cash['calculated_salary'], kpi_cash['penalty'],
                workshift.shortage, final_salary_cash
            ]

            if not hall_admin_dict.get(workshift.hall_admin.profile.get_name()):
                print(f'Add {workshift.hall_admin.profile.get_name()}')
                hall_admin_dict[workshift.hall_admin.profile.get_name()] = [ hall_values_list, ]
            else:
                hall_admin_dict[workshift.hall_admin.profile.get_name()].append(hall_values_list)

            if not cash_admin_dict.get(workshift.cash_admin.profile.get_name()):
                print(f'Add {workshift.cash_admin.profile.get_name()}')
                cash_admin_dict[workshift.cash_admin.profile.get_name()] = [ cash_values_list, ]
            else:
                cash_admin_dict[workshift.cash_admin.profile.get_name()].append(cash_values_list)

        employee_list = []

        for name, values in hall_admin_dict.items():
            hall_admin_list = [name, len(values)]
            kpi_values = [round(sum(a), 2) for a in zip(*values)]
            hall_admin_list.extend(kpi_values)
            employee_list.append(hall_admin_list)

        for name, values in cash_admin_dict.items():
            cash_admin_list = [name, len(values)]
            kpi_values = [round(sum(a), 2) for a in zip(*values)]
            cash_admin_list.extend(kpi_values)
            employee_list.append(cash_admin_list)

        context['employee_list'] = employee_list
        context['current_date'] = datetime.date.today()
        context['title'] = 'Monthly Report'

        return context


def page_not_found(request, exception):
    response = render(request, 'salary/404.html', {'title': 'Page not found'})
    response.status_code = 404
    return response


def page_forbidden(request, exception):
    response = render(request, 'salary/403.html', {'title': 'Access forbidden'})
    response.status_code = 403
    return response