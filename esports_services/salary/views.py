from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView
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
        context['experience'] = self.get_work_experience()
        context['tables'] = self.get_user_workshifts(month=current_month, year=current_year)
        context['total_values'] = self.get_total_values(self.request.user, context['tables'])
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

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['start_date'] = context['object'].shift_date - relativedelta(days=1)
        return context


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