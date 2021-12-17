from django.contrib.auth.forms import AuthenticationForm
from django.http import request
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import *

import datetime


def registration(request):
    if request.method == 'POST':
        user_form = UserRegistration(request.POST)
        profile_form = EmployeeRegistration(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
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
        context['title'] = 'Authorization'
        return context

    def get_success_url(self, **kwargs):
        return reverse_lazy('index')


class IndexView(LoginRequiredMixin, TemplateView):
    login_url = 'login/'
    template_name = 'salary/account.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Личный кабинет'
        context['experience'] = self.get_work_experience()
        return context

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
            if 1 < month < 5:
                experience_text += 'а '
            else:
                experience_text += 'ев '

        experience_text += str(days) + ' д'
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