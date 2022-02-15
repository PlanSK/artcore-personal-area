from signal import pause
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
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


# Registration, Login, Logout
def registration(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = EmployeeRegistrationForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False) 
            profile = profile_form.save(commit=False)
            user.is_active = False
            profile.user = user
            user.save()
            profile.save()
            return redirect('login')
    else:
        user_form = UserRegistrationForm()
        profile_form = EmployeeRegistrationForm()
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


def logout_user(request):
    logout(request)
    return redirect('login')


# Staff Functionality
class StaffUserView(StaffPermissionRequiredMixin, TotalDataMixin, TemplateView):
    template_name = 'salary/staff_user_view.html'

    def dispatch(self, request, *args: Any, **kwargs: Any):
        self.required_year = self.kwargs.get('year')
        self.required_month = self.kwargs.get('month')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_user = self.kwargs.get('request_user')
        get_user = get_object_or_404(User, username=request_user)
        workshifts = WorkingShift.objects.filter(
            shift_date__year=self.required_year,
            shift_date__month=self.required_month
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


class ReportsView(StaffPermissionRequiredMixin, TitleMixin, ListView):
    template_name = 'salary/reports_list.html'
    model = WorkingShift
    title = 'Отчеты'

    def get_queryset(self):
        query = WorkingShift.objects.dates('shift_date', 'month')
        return query


class AdminWorkshiftsView(StaffPermissionRequiredMixin, TitleMixin, ListView):
    template_name = 'salary/staff_view_workshifts.html'
    model = WorkingShift
    title = 'Смены'
    paginate_by = 5

    def get_queryset(self):
        workshifts = WorkingShift.objects.filter(is_verified=False).select_related(
            'hall_admin__profile',
            'cash_admin__profile',
        )
        if self.kwargs.get('all'):
            workshifts = WorkingShift.objects.all().select_related(
                'hall_admin__profile',
                'cash_admin__profile',
            )

        return workshifts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.kwargs.get('all'):
            context['only_verified'] = True
        return context


class DeleteWorkshift(PermissionRequiredMixin, TitleMixin, DeleteView):
    model = WorkingShift
    permission_required = 'salary.delete_workingshift'
    success_url = reverse_lazy('index')
    title = 'Удаление смены'


class MonthlyReportListView(PermissionRequiredMixin, StaffOnlyMixin, ListView):
    model = WorkingShift
    permission_required = 'salary.view_workingshift'
    template_name = 'salary/monthlyreport_list.html'

    def dispatch(self, request, *args, **kwargs):
        self.year = self.kwargs.get('year')
        self.month = self.kwargs.get('month')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        workshifts = WorkingShift.objects.select_related(
            'cash_admin__profile__position',
            'hall_admin__profile__position',
        ).filter(
            shift_date__month=self.month,
            shift_date__year=self.year,
            is_verified=True
        )

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
        users_list = [(obj.hall_admin, obj.cash_admin) for obj in context['object_list']]
        users = dict()
        for hall_admin, cash_admin in users_list:
            users.update({
               hall_admin.get_full_name(): hall_admin,
               cash_admin.get_full_name(): cash_admin,
            })
        context.update({
            'employee_list': self.get_employee_list(context['object_list']),
            'current_date': datetime.date(self.year, self.month, 1),
            'users': users,
            'title': 'Авансовый отчет'
        })

        return context


class AddPublicationView(StaffPermissionRequiredMixin, TitleMixin, CreateView):
    title = 'Добавление публикации'
    form_class = AddPublicationForm
    template_name = 'salary/publication_form.html'
    success_url = reverse_lazy('publications')

    def get_initial(self):
        initional = super().get_initial()
        initional.update({
            'auditor': self.request.user,
        })
        return initional


class PublicationListView(StaffPermissionRequiredMixin, TitleMixin, ListView):
    title = 'Список смен'
    model = Publication
    template_name = 'salary/publication_list.html'

    def get_queryset(self):
        queryset = Publication.objects.select_related('author', 'auditor').order_by('publication_date')

        return queryset

class EditPublicationView(StaffPermissionRequiredMixin, TitleMixin, UpdateView):
    model = Publication
    form_class = EditPublicationForm
    title = 'Изменение публикации'
    template_name = 'salary/publication_form.html'
    success_url = reverse_lazy('publications')

class DeletePublication(StaffPermissionRequiredMixin, TitleMixin, DeleteView):
    model = Publication
    success_url = reverse_lazy('publications')
    title = 'Удаление смены'

# Employee functionality
class EditUser(LoginRequiredMixin, TitleMixin, TemplateView):
    template_name = 'salary/edit_user_profile.html'
    title = 'Редактирование пользователя'
    userform = EditUserForm
    profileform = EditProfileForm

    def dispatch(self, request, *args: Any, **kwargs: Any):
        if self.kwargs.get('pk'):
            self.edited_user = get_object_or_404(User.objects.select_related('profile'), pk=self.kwargs.get('pk', 0))
        else:
            self.edited_user = self.request.user
        self.redirect_link = request.GET.get('next', reverse_lazy('index'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args: Any, **kwargs: Any):
        user_form_class = self.userform(instance=self.edited_user)
        profile_form_class = self.profileform(instance=self.edited_user.profile)
        context = self.get_context_data(
            profile_form=profile_form_class,
            user_form=user_form_class
        )
        return render(request, self.template_name, context=context)

    def post(self, request, **kwargs):
        user_form_class = self.userform(request.POST, instance=self.edited_user)
        profile_form_class = self.profileform(request.POST, request.FILES, instance=self.edited_user.profile)
        if user_form_class.is_valid() and profile_form_class.is_valid():
            user = user_form_class.save(commit=False)
            profile = profile_form_class.save(commit=False)
            user.save()
            profile.user = user
            profile.save()
            return HttpResponseRedirect(self.redirect_link)
        else:
            user_form_class = self.userform
            profile_form_class = self.profileform
            context = self.get_context_data(
                profile_form=profile_form_class,
                user_form=user_form_class
            )
            return render(request, self.template_name, context=context)


class StaffEditUser(StaffPermissionRequiredMixin, EditUser):
    userform = StaffEditUserForm
    profileform = StaffEditProfileForm
    title = 'Редактирование профиля'


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
        current_workshifts = self.get_user_workshifts(month=current_month, year=current_year)

        previous_date = datetime.date(current_year, current_month, 1) - relativedelta(months=1)
        next_date = datetime.date(current_year, current_month, 1) + relativedelta(months=1)
        if self.get_user_workshifts(month=previous_date.month, year=previous_date.year):
            context['previous_date'] = previous_date
        if self.get_user_workshifts(month=next_date.month, year=next_date.year):
            context['next_date'] = next_date

        context.update({
            'current_date': datetime.date(current_year, current_month, 1),
            'experience': self.request.user.profile.get_work_experience,
            'workshifts': current_workshifts,
            'total_values': self.get_total_values(self.request.user, current_workshifts),
            'current_workshift': self.get_current_shift(),
        })

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


class AddWorkshiftData(PermissionRequiredMixin, TitleMixin, CreateView):
    form_class = AddWorkshiftDataForm
    permission_required = 'salary.add_workingshift'
    template_name = 'salary/add_workshift.html'
    success_url = reverse_lazy('index')
    title = 'Добавление смен'

    def get_initial(self):
        initional = super().get_initial()
        initional.update({
            'cash_admin': self.request.user,
            'shift_date': datetime.date.today().strftime('%Y-%m-%d'),
        })
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


# Additional functionality
def page_not_found(request, exception):
    response = render(request, 'salary/404.html', {'title': 'Page not found'})
    response.status_code = 404
    return response


def page_forbidden(request, exception):
    response = render(request, 'salary/403.html', {'title': 'Access forbidden'})
    response.status_code = 403
    return response