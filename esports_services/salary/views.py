from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, ListView
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.db.models import Q

from .forms import *
from .utils import *

import datetime
from typing import *
from dateutil.relativedelta import relativedelta


def registration(request):
    if request.method == 'POST':
        user_form = UserRegistration(request.POST)
        profile_form = EmployeeRegistration(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False) 
            profile = profile_form.save(commit=False)
            user.is_active = False
            profile.user = user
            user.save()
            profile.save()
            return redirect('login')
    else:
        user_form = UserRegistration()
        profile_form = EmployeeRegistration()
    context = {
        'title': 'Регистрация сотрудника',
        'form': user_form,
        'employee_form': profile_form
    }
    return render(request, 'salary/registration.html', context=context)


class LoginUser(TitleMixin, LoginView):
    template_name = 'salary/login.html'
    form_class = AuthenticationForm
    redirect_authenticated_user = True
    title = 'Авторизация'

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
        ).filter(Q(cash_admin=get_user) | Q(hall_admin=get_user))
        context['title'] = f'Данные польователя {get_user}'
        context['request_user'] = get_user
        context['workshifts'] = workshifts
        context['total_values'] = self.get_total_values(get_user, workshifts)

        return context

class AdminView(StaffPermissionRequiredMixin, StaffOnlyMixin, TitleMixin, TemplateView):
    template_name = 'salary/dashboard.html'
    login_url = 'login'
    title = 'Панель управления'


class AdminUserView(StaffPermissionRequiredMixin, TitleMixin, ListView):
    template_name = 'salary/show_users.html'
    model = User
    title = 'Управление персоналом'

    def get_queryset(self):
        query = User.objects.exclude(is_staff=True).select_related(
            'profile',
            'profile__position'
        ).order_by('-profile__position')
        return query


class AdminWorkshiftsView(StaffPermissionRequiredMixin, TitleMixin, ListView):
    template_name = 'salary/staff_view_workshifts.html'
    model = WorkingShift
    title = 'Смены'
    paginate_by = 5

    def get_queryset(self):
        if self.kwargs.get('all'):
            workshifts = WorkingShift.objects.all().select_related(
                'hall_admin__profile',
                'cash_admin__profile',
            )
        else:
            workshifts = WorkingShift.objects.filter(is_verified=False).select_related(
                'hall_admin__profile',
                'cash_admin__profile',
            )

        return workshifts
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.kwargs.get('all'):
            context['only_verified'] = True
        return context


class StaffEditUser(StaffPermissionRequiredMixin, TitleMixin, TemplateView):
    template_name = 'salary/edit_user_profile.html'
    fields = ('first_name','last_name', 'email', 'is_active')
    title = 'Редактирование пользователя'


class IndexView(LoginRequiredMixin, TotalDataMixin, TemplateView):
    login_url = 'login'
    template_name = 'salary/account.html'

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)

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
        ).filter(Q(cash_admin=self.request.user) | Q(hall_admin=self.request.user))

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


class AddWorkshiftData(PermissionRequiredMixin, TitleMixin, CreateView):
    form_class = AddWorkshiftDataForm
    permission_required = 'salary.add_workingshift'
    template_name = 'salary/add_workshift.html'
    success_url = reverse_lazy('index')
    title = 'Добавление смен'

    def get_initial(self):
        initional = super().get_initial()
        initional['cash_admin'] = self.request.user
        initional['shift_date'] = datetime.date.today().strftime('%Y-%m-%d')
        return initional


class EditWorkshiftData(PermissionRequiredMixin, UpdateView):
    model = WorkingShift
    form_class = EditWorkshiftDataForm
    permission_required = 'salary.change_workingshift'
    template_name = 'salary/edit_workshift.html'
    success_url = reverse_lazy('index')
    
    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['start_date'] = context['object'].shift_date - relativedelta(days=1)
        return context


class StaffEditWorkshift(StaffOnlyMixin, EditWorkshiftData):
    form_class = StaffEditWorkshiftForm


class DeleteWorkshift(PermissionRequiredMixin, TitleMixin, DeleteView):
    model = WorkingShift
    permission_required = 'salary.delete_workingshift'
    success_url = reverse_lazy('index')
    title = 'Удаление смены'


class MonthlyReportListView(PermissionRequiredMixin, StaffOnlyMixin, ListView):
    model = WorkingShift
    permission_required = 'salary.view_workingshift'
    template_name = 'salary/monthlyreport_list.html'

    def get_queryset(self):
        month = datetime.date.today().month
        workshifts = WorkingShift.objects.select_related(
            'cash_admin__profile__position',
            'hall_admin__profile__position',
        ).filter(shift_date__month=month, is_verified=True)

        return workshifts

    def get_values_list(self, kpi_dict: dict, shortage=0.0) -> list:
        if kpi_dict['penalty'] > 1000:
            penalty = 1000
        else:
            penalty = kpi_dict['penalty']

        final_salary_hall = kpi_dict['calculated_salary'] - penalty
        values_list = [
            1, kpi_dict['calculated_salary'],
            kpi_dict['penalty'], shortage, final_salary_hall
        ]
        return values_list

    def get_employee_list(self, objects: list) -> list:
        users_dict = dict()

        for workshift in objects:
            current_user_dict = {
                workshift.hall_admin.get_full_name(): self.get_values_list(
                    workshift.kpi_salary_calculate(workshift.hall_admin)),
                workshift.cash_admin.get_full_name(): self.get_values_list(
                    workshift.kpi_salary_calculate(workshift.cash_admin),
                    shortage=workshift.shortage)
            }

            for name, values in current_user_dict.items():
                if users_dict.get(name):
                    users_dict[name] = [
                        round(sum(a), 2)
                        for a in zip(users_dict[name], values)
                    ]
                else:
                    users_dict.update({name: list(map(lambda x: round(x, 2), values))})

        employee_list = []

        for name, values in users_dict.items():
            employee_list.append([name] + values)

        employee_list.sort(key=lambda x: x[-1], reverse=1)


        return employee_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'employee_list': self.get_employee_list(context['object_list']),
            'current_date': datetime.date.today(),
            'title': 'Авансовый отчет'
        })

        return context


def page_not_found(request, exception):
    response = render(request, 'salary/404.html', {'title': 'Page not found'})
    response.status_code = 404
    return response


def page_forbidden(request, exception):
    response = render(request, 'salary/403.html', {'title': 'Access forbidden'})
    response.status_code = 403
    return response