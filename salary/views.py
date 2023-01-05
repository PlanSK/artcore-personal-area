import datetime
from typing import *
from dateutil.relativedelta import relativedelta
import logging

from django.contrib.auth.forms import AuthenticationForm, AdminPasswordChangeForm
from django.http import Http404, HttpRequest, JsonResponse, HttpResponseNotFound, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.base import RedirectView
from django.db.models import Q, QuerySet, Sum, Avg

from .forms import *
from .mixins import *
from salary.services.chat import *
from salary.services.shift_calendar import (get_user_calendar,
                                            get_employee_on_work)
from salary.services.misconduct import Intruder
from salary.services.internal_model_func import get_misconduct_slug
from salary.services.workshift import (
    notification_of_upcoming_shifts, get_missed_dates_tuple,
    get_employee_workshift_indicators, get_employee_month_workshifts,
    get_employee_unclosed_workshifts_dates, get_unclosed_workshift_number
)
from salary.services.registration import (
    registration_user, sending_confirmation_link, confirmation_user_email,
    get_user_instance_from_uidb64, authentification_user, add_user_to_groups
)
from salary.services.filesystem import (
    get_employee_documents_urls, document_file_handler,
    delete_document_from_storage
)
from salary.services.monthly_reports import (
    get_monthly_report, get_awards_data, get_filtered_rating_data
)
from salary.services.misconduct import get_misconduct_employee_data
from salary.services.profile_services import get_birthday_person_list


logger = logging.getLogger(__name__)


class RegistrationUser(TitleMixin, SuccessUrlMixin, TemplateView):
    template_name = 'salary/auth/registration.html'
    success_template_name = 'salary/auth/registration_link_wait.html'
    title = 'Регистрация сотрудника'
    user_form = UserRegistrationForm
    profile_form = EmployeeRegistrationForm

    def get(self, request: HttpRequest,
            *args: Any, **kwargs: Any) -> HttpResponse:

        context = self.get_context_data(
            profile_form=self.profile_form,
            user_form=self.user_form
        )
        return render(request, self.template_name, context=context)

    def post(self, request: HttpRequest,
             *args: Any, **kwargs: Any) -> HttpResponse:

        user_form = self.user_form(request.POST)
        profile_form = self.profile_form(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = registration_user(
                request=request,
                user_form=user_form,
                profile_form=profile_form
            )

            context = { 'first_name': user.first_name }
            return render(request, self.success_template_name, context=context)
        else:
            context = self.get_context_data(
                profile_form=profile_form,
                user_form=user_form
            )
            return render(request, self.template_name, context=context)


def request_confirmation_link(request):
    username = request.POST.get('user')
    sending_confirmation_link(request=request, username=username)

    return HttpResponse('Success sent.')


class ConfirmUserView(TitleMixin, SuccessUrlMixin, TemplateView):
    template_name = 'salary/auth/email_confirmed.html'
    title = 'Учетная запись активирована'

    def dispatch(self, request, *args: Any, **kwargs: Any):
        user_uidb64 = kwargs.get('uidb64')
        request_token = kwargs.get('token')

        confirmation_user_email(
            request=request,
            user_uidb64_str=user_uidb64,
            request_token=request_token
        )
        self.requested_user = get_user_instance_from_uidb64(
            uidb64_str=user_uidb64
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['first_name'] = self.requested_user.first_name
        return context


class ConfirmMailStatus(EmployeePermissionsMixin, TitleMixin, ListView):
    model = User
    title = 'Состояние активации учетных записей.'
    template_name = 'salary/staff_user_confirmation_status.html'

    def get_queryset(self):
        queryset = User.objects.select_related('profile').filter(
            profile__dismiss_date=None
        ).exclude(profile__position=4)

        return queryset


class DismissalEmployee(EmployeePermissionsMixin, TitleMixin,
                        SuccessUrlMixin, TemplateView):
    model = Profile
    title = 'Увольнение сотрудника'
    template_name = 'salary/dismissal_user.html'
    profile_form = DismissalEmployeeForm

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(
            User.objects.select_related('profile'),
            pk=self.kwargs.get('pk', 0)
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        profile_form_class = self.profile_form(instance=self.object.profile)
        context = self.get_context_data(
            profile_form=profile_form_class,
        )
        return render(request, self.template_name, context=context)

    def post(self, request, **kwargs):
        profile_form_class = self.profile_form(request.POST, instance=self.object.profile)
        if profile_form_class.is_valid():
            profile = profile_form_class.save(commit=False)
            profile.profile_status = Profile.ProfileStatus.DISMISSED
            self.object.groups.clear()
            self.object.user_permissions.clear()
            self.object.is_active = False
            self.object.save()
            return redirect(self.get_success_url())
        else:
            context = self.get_context_data(
                profile_form=profile_form_class,
            )
            return render(request, self.template_name, context=context)


class LoginUser(TitleMixin, SuccessUrlMixin, LoginView):
    template_name = 'salary/login.html'
    form_class = AuthenticationForm
    redirect_authenticated_user = True
    title = 'Авторизация'


class EmployeePasswordChangeView(TitleMixin, SuccessUrlMixin, PasswordChangeView):
    title = 'Смена пароля'
    template_name = 'salary/auth/password_change.html'


class StaffPasswordChangeView(EmployeePermissionsMixin, TitleMixin, 
                                SuccessUrlMixin, PasswordChangeView):
    title = 'Задать пароль'
    template_name = 'salary/auth/password_change.html'
    form_class = AdminPasswordChangeForm


def logout_user(request):
    logout(request)
    return redirect('login')


class AdminUserView(EmployeePermissionsMixin, TitleMixin, ListView):
    template_name = 'salary/show_users.html'
    model = User
    title = 'Управление персоналом'

    def get_queryset(self):
        queryset = User.objects.select_related(
            'profile', 'profile__position').order_by(
                '-profile__position').exclude(profile__position=4)

        if not self.kwargs.get('all'):
            return queryset.filter(profile__dismiss_date__isnull=True)

        return queryset

    def get_context_data(self, **kwargs):
        context: dict = super().get_context_data(**kwargs)
        context.update({
            'attestation_enabled': settings.ATTESTATION_ENABLED,
            'only_actived': True if not self.kwargs.get('all') else False
        })
        return context


class ReportsView(WorkingshiftPermissonsMixin, TitleMixin, ListView):
    template_name = 'salary/reports_list.html'
    model = WorkingShift
    title = 'Отчеты'

    def get_queryset(self):
        query = WorkingShift.objects.filter(
            status=WorkingShift.WorkshiftStatus.VERIFIED
        ).dates('shift_date','month')
        return query


class AnalyticalView(ReportsView):
    template_name = 'salary/analytical_reports_list.html'


class StaffWorkshiftsView(WorkingshiftPermissonsMixin, MonthYearExtractMixin,
                          TitleMixin, ListView):
    template_name = 'salary/staff_workshifts_view.html'
    model = WorkingShift
    title = 'Смены'

    def get_queryset(self):
        workshifts = WorkingShift.objects.select_related('hall_admin',
                                                         'cash_admin')
        return workshifts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'workshift_list': self.object_list.exclude(
                status=WorkingShift.WorkshiftStatus.VERIFIED),
            'missed_workshifts_dates': get_missed_dates_tuple(),
        })
        return context


class StaffIndexView(WorkingshiftPermissonsMixin, TitleMixin,
                          TemplateView):
    template_name = 'salary/staff/staff_index.html'
    title = 'Главная'
    
    def get_context_data(self, **kwargs):
        context : dict = super().get_context_data(**kwargs)
        employees_on_work = get_employee_on_work()
        today_date = timezone.localdate(timezone.now())
        birthday_person_list = get_birthday_person_list(day=today_date.day,
                                                        month=today_date.month)
        context.update({
            'employee_on_work': employees_on_work,
            'today_date': today_date,
            'missed_workshifts_dates': get_missed_dates_tuple(),
            'birthday_person_list': birthday_person_list,
            'unread_messages_number': get_unread_messages_number(
                self.request.user),
            'unclosed_workshifts': get_unclosed_workshift_number(),
            'total_rating_data': get_filtered_rating_data(today_date.month,
                                                          today_date.year)
        })
        return context


class StaffArchiveWorkshiftsView(WorkingshiftPermissonsMixin,
                                 MonthYearExtractMixin, TitleMixin, ListView):
    template_name = 'salary/staff_workshifts_view.html'
    model = WorkingShift
    title = 'Смены'
    context_object_name = 'workshift_list'

    def get_queryset(self):
        if self.kwargs.get('year') and self.kwargs.get('month'):
            queryset = WorkingShift.objects.filter(
                shift_date__month = self.month,
                shift_date__year = self.year
            ).select_related('cash_admin', 'hall_admin').order_by('shift_date')
        else:
            HttpResponseNotFound('No all data found.')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'summary_revenue': sum([
                workshift.summary_revenue
                for workshift in self.object_list
            ]),
            'workshift_dates': datetime.date(
                self.year, self.month, 1
            ),
            'missed_workshifts_dates': get_missed_dates_tuple(),
        })

        return context


class StaffWorkshiftsMonthlyList(WorkingshiftPermissonsMixin, TitleMixin, 
                                    ListView):
    template_name = 'salary/staff_monthly_workshifts_list.html'
    model = WorkingShift
    title = 'Смены'

    def get_queryset(self):
        workshifts_months = WorkingShift.objects.dates('shift_date', 'month')
        return workshifts_months


class DeleteWorkshift(WorkingshiftPermissonsMixin, TitleMixin, SuccessUrlMixin,
                        DeleteView):
    model = WorkingShift
    title = 'Удаление смены'


class MonthlyReportListView(WorkingshiftPermissonsMixin, MonthYearExtractMixin,
                            TitleMixin, TemplateView):
    template_name = 'salary/monthlyreport_list.html'
    title = 'Сводный отчёт'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'report_data': get_monthly_report(month=self.month,
                                                  year=self.year),
            'current_date': datetime.date(self.year, self.month, 1),
        })

        return context


class AddMisconductView(MisconductPermissionsMixin, TitleMixin, SuccessUrlMixin,
                        CreateView):
    model = Misconduct
    title = 'Добавление дисциплинарного проступка'
    form_class = AddMisconductForm

    def form_valid(self, form):
        object = form.save(commit=False)
        object.moderator = self.request.user
        object.editor = self.request.user.get_full_name()
        slug_name = get_misconduct_slug(
            object.intruder.last_name,
            object.misconduct_date,
        )
        count = Misconduct.objects.filter(slug__startswith=slug_name).count()
        object.slug = slug_name if not count else f'{slug_name}-{count}'

        return super().form_valid(form)


def load_regulation_data(request: HttpRequest) -> JsonResponse:
    requested_article = request.POST.get('regulations_article')
    regulation_article = get_object_or_404(
        DisciplinaryRegulations,
        pk=requested_article,
    )
    response = {
        'article_number': regulation_article.article,
        'title': regulation_article.title,
        'sanction': regulation_article.sanction,
        'penalty': regulation_article.base_penalty,
    }

    return JsonResponse(response)


class MisconductListView(MisconductPermissionsMixin, TitleMixin, ListView):
    model = Misconduct
    title = 'Список нарушителей'
    template_name = 'salary/intruders_list.html'

    def get_queryset(self) -> List[Intruder]:
        queryset = Misconduct.objects.select_related('intruder__profile')

        if not self.request.GET.get('show'):
            queryset = queryset.exclude(intruder__profile__profile_status='DSM')

        intruders_dict = dict()
        for misconduct in queryset:
            if intruders_dict.get(misconduct.intruder):
                intruders_dict[misconduct.intruder].append(misconduct.status)
            else:
                intruders_dict[misconduct.intruder] = [misconduct.status,]
        
        intruders_list = [
            Intruder(
                employee=intruder,
                total_count=len(intruders_dict[intruder]),
                explanation_count=len(
                    list(filter(
                        lambda x: x == 'AD',
                        intruders_dict[intruder]
                    ))
                ),
                decision_count=len(
                    list(filter(
                        lambda x: x == 'WT',
                        intruders_dict[intruder]
                    ))
                )
            ) for intruder in intruders_dict.keys()
        ]
        sorted_intruders_list = sorted(
            intruders_list, key=lambda i: i.total_count, reverse=True
        )

        return sorted_intruders_list
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.GET.get('show'):
            context['only_actived'] = True
        return context


class MisconductUserView(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                            TitleMixin, ListView):
    model = Misconduct
    title = 'Нарушения'
    permission_required = 'salary.view_misconduct'

    def dispatch(self, request, *args: Any, **kwargs: Any):
        self.intruder = self.kwargs.get('username')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Misconduct.objects.filter(intruder__username=self.intruder).select_related('intruder', 'regulations_article')

    def get_penalty_sum(self) -> float:
        """Возвращает сумму штрафов по нарушениям

        Returns:
            float: сумма штрафов (число типа float)
        """
        if self.object_list.filter(status=Misconduct.MisconductStatus.CLOSED):
            return self.object_list.filter(
                status=Misconduct.MisconductStatus.CLOSED,
            ).aggregate(Sum('penalty')).get('penalty__sum')
        
        return 0.0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'intruder': get_object_or_404(User, username=self.intruder),
            'penalty_sum': self.get_penalty_sum(),
        })

        return context


class MisconductUpdateView(MisconductPermissionsMixin, TitleMixin, 
                            EditModelEditorFieldsMixin, SuccessUrlMixin, UpdateView):
    model = Misconduct
    title = 'Редактирование данных нарушения'
    form_class = EditMisconductForm


class MisconductDeleteView(MisconductPermissionsMixin, TitleMixin,
                            SuccessUrlMixin, DeleteView):
    model = Misconduct
    title = 'Удаление нарушения'


class EditUser(ProfileStatusRedirectMixin, TitleMixin, SuccessUrlMixin,
               TemplateView):
    template_name = 'salary/edit_user_profile.html'
    title = 'Редактирование пользователя'
    userform = EditUserForm
    profileform = EditProfileForm

    def dispatch(self, request, *args: Any, **kwargs: Any):
        if self.kwargs.get('pk'):
            self.edited_user = get_object_or_404(
                User.objects.select_related('profile'),
                pk=self.kwargs.get('pk', 0)
            )
        else:
            self.edited_user = self.request.user
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
            if 'email' in user_form_class.changed_data:
                self.edited_user.profile.email_status = Profile.EmailStatus.ADDED
            user = user_form_class.save(commit=False)
            profile = profile_form_class.save(commit=False)
            user.save()
            profile.save()
            add_user_to_groups(user)
            return redirect(self.get_success_url())
        else:
            user_form_class = self.userform
            profile_form_class = self.profileform
            context = self.get_context_data(
                profile_form=profile_form_class,
                user_form=user_form_class
            )
            return render(request, self.template_name, context=context)


class StaffEditUser(EmployeePermissionsMixin, EditUser):
    userform = StaffEditUserForm
    profileform = StaffEditProfileForm
    title = 'Редактирование профиля'


class ShowUserProfile(LoginRequiredMixin, TitleMixin, DetailView):
    model = User
    title = 'Просмотр профиля'
    queryset = User.objects.select_related('profile')
    template_name = 'salary/user_detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            queryset if queryset else self.get_queryset(),
            pk=self.request.user.pk
        )
    
    def get_context_data(self, **kwargs):
        context : dict = super().get_context_data(**kwargs)
        context.update(
            {
                'attestation_enabled': settings.ATTESTATION_ENABLED
            }
        )
        return context


class WorkshiftDetailView(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                            TitleMixin, DetailView):
    model = WorkingShift
    title = 'Детальный просмотр смены'
    permission_required = 'salary.view_workingshift'
    queryset = WorkingShift.objects.select_related(
            'cash_admin__profile__position',
            'hall_admin__profile__position',
    )
    context_object_name = 'workshift'

    def get_context_data(self, **kwargs):
        context: dict = super().get_context_data(**kwargs)
        yesterday = context['object'].shift_date - datetime.timedelta(days=1)
        context.update({
            'yesterday': yesterday,
            'attestation_enabled': settings.ATTESTATION_ENABLED,
            'publication_enabled': settings.PUBLICATION_ENABLED
        })

        return context

class MisconductDetailView(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                            TitleMixin, DetailView):
    model = Misconduct
    title = 'Протокол нарушения'
    permission_required = 'salary.view_misconduct'
    context_object_name = 'misconduct'
    queryset = Misconduct.objects.select_related('intruder', 'moderator',
                                                 'regulations_article')


class MonthlyAnalyticalReport(WorkingshiftPermissonsMixin, 
                              MonthYearExtractMixin, TitleMixin, ListView):
    model = WorkingShift
    title = 'Аналитический отчёт'
    template_name = 'salary/monthly_analytical_report.html'

    def get_queryset(self) -> QuerySet:
        queryset = WorkingShift.objects.all().select_related(
            'hall_admin',
            'cash_admin',
        ).order_by('shift_date')
        return queryset

    def get_fields_dict(self) -> dict:
        fields = (
            'summary_revenue', 'bar_revenue', 'game_zone_subtotal',
            'game_zone_error', 'additional_services_revenue', 'hookah_revenue',
            'shortage', 'summary_revenue__avg',
        )
        self.current_month_queryset = self.object_list.filter(
            shift_date__month=self.month,
            shift_date__year=self.year,
        )

        if not self.current_month_queryset:
            raise Http404

        self.current_date = datetime.date(self.year, self.month, 1)

        self.previous_month_date = self.current_date - relativedelta(months=1)
        self.previous_month_queryset = self.object_list.filter(
            shift_date__month=self.previous_month_date.month,
            shift_date__year=self.previous_month_date.year,
        )

        values_dict = dict()
        operations_list = [
            Sum(field) if '__avg' not in field
            else Avg(field.split('__')[0])
            for field in fields
        ]

        current_month_values = self.current_month_queryset.aggregate(*operations_list)
        previous_month_values = self.previous_month_queryset.aggregate(*operations_list)

        for field in current_month_values.keys():
            current_month_value = round(current_month_values.get(field, 0), 2)
            previous_month_value = round(
                previous_month_values.get(field, 0), 2
            ) if previous_month_values.get(field, 0) else 0

            if current_month_value == 0.0:
                ratio = 100.0
            elif current_month_value > previous_month_value:
                ratio = round((current_month_value - previous_month_value) /
                            current_month_value * 100, 2)
            elif current_month_value < previous_month_value:
                ratio = round((previous_month_value - current_month_value) /
                            previous_month_value * 100, 2)

            values_dict[field] = (
                        previous_month_value,
                        current_month_value,
                        ratio,
                    )

        return values_dict

    def get_linechart_data(self) -> list:
        """Return list of lists with revenue data for Google LineChart

        Returns:
            list: list of lists [day_of_month, previous_month_revenue, current_month_revenue]
        """
        current_month_list =  self.current_month_queryset.values_list(
            'shift_date__day',
            'summary_revenue')
        previous_month_list = self.previous_month_queryset.values_list(
            'shift_date__day',
            'summary_revenue')
        linechart_data_list = list()
        for first_element in previous_month_list:
            for second_element in current_month_list:
                if first_element[0] == second_element[0]:
                    data_row = list(first_element)
                    data_row.append(second_element[1])
                    linechart_data_list.append(data_row)

        return linechart_data_list

    def get_piechart_data(self, analytic_data: dict) -> list:
        categories = {
            'bar_revenue': 'Бар',
            'game_zone_subtotal': 'Game zone',
            'additional_services_revenue': 'Доп. услуги',
            'hookah_revenue': 'Кальян',
        }

        piechart_data = list()

        for category in categories.keys():
            piechart_data.append(
                [categories.get(category), analytic_data.get(f'{category}__sum')[1]]
            )

        return piechart_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        analytic_data = self.get_fields_dict()
        context.update({
            'analytic': analytic_data,
            'piechart_data': self.get_piechart_data(analytic_data),
            'min_revenue_workshift': self.current_month_queryset.order_by(
                'summary_revenue').first(),
            'max_revenue_workshift': self.current_month_queryset.order_by(
                'summary_revenue').last(),
            'current_month_date': self.current_date,
            'previous_month_date': self.previous_month_date,
            'linechart_data': self.get_linechart_data(),
        })

        return context


class IndexEmployeeView(LoginRequiredMixin, ProfileStatusRedirectMixin,
                        TitleMixin, TemplateView):
    """
    Class based view Index page for any employee.
    Redirect user with staff status to staff index page.
    """

    template_name = 'salary/employee_board.html'
    title = 'Панель пользователя'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        logger.debug('Check user staff status.')
        if request.user.is_authenticated and request.user.is_staff:
            logger.debug('Redirect to staff page.')
            return redirect('staff_index')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        logger.debug(
            f'Get user {self.request.user.username} context data.'
        )
        context = super().get_context_data(**kwargs)

        notification_about_shift = notification_of_upcoming_shifts(
            user=self.request.user)
        misconduct_data = get_misconduct_employee_data(self.request.user.id)
        employee_month_indicators = get_employee_workshift_indicators(
            self.request.user.id)
        unclosed_shifts_dates = get_employee_unclosed_workshifts_dates(
            self.request.user.id)

        logger.debug(
            f'Shifts to close number: {len(unclosed_shifts_dates)}. '
            f'Notofication: {notification_about_shift}.'
        )
        context.update({
            'employee_indicators': employee_month_indicators,
            'misconduct_data': misconduct_data,
            'today_date': timezone.localdate(timezone.now()),
            'unclosed_shifts_dates': unclosed_shifts_dates,
            'notification_about_shift': notification_about_shift,
            'minimal_workshifts_number': settings.MINIMAL_WORKSHIFTS_NUMBER
        })
        logger.debug('Context data is updated. Return context.')
        return context


class EmployeeWorkshiftsView(PermissionRequiredMixin, MonthYearExtractMixin,
                             TitleMixin, TemplateView):
    template_name = 'salary/employee_workshifts_view.html'
    title = 'Смены'
    permission_required = 'salary.view_workingshift'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        workshifts_list = get_employee_month_workshifts(
            self.request.user.id, self.month, self.year)
        employee_month_indicators = get_employee_workshift_indicators(
            self.request.user.id, self.month, self.year)
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'employee_indicators': employee_month_indicators,
                'workshifts_list': workshifts_list
            }
        )
        return context


class EmployeeMonthlyListView(ProfileStatusRedirectMixin, 
                              PermissionRequiredMixin, TitleMixin, ListView):
    template_name = 'salary/employee_monthly_list.html'
    title = 'Архив смен'
    permission_required = 'salary.view_workingshift'

    def get_queryset(self) -> QuerySet:
        queryset = WorkingShift.objects.select_related(
            'hall_admin__profile__position',
            'cash_admin__profile__position'
        ).filter(
            Q(cash_admin=self.request.user) | Q(hall_admin=self.request.user)
        ).dates('shift_date', 'month')

        return queryset


class StaffEmployeeMonthView(WorkingshiftPermissonsMixin,
                             MonthYearExtractMixin, TitleMixin, ListView):
    template_name = 'salary/staff_employee_month_view.html'
    title = 'Просмотр смен'

    def dispatch(self, request, *args: Any, **kwargs: Any):
        self.employee = get_object_or_404(User, pk=self.kwargs.get('employee'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        queryset = WorkingShift.objects.select_related(
            'hall_admin__profile__position',
            'cash_admin__profile__position'
        ).filter(
            shift_date__month=self.month,
            shift_date__year=self.year,
        ).filter(
            Q(cash_admin=self.employee) | Q(hall_admin=self.employee)
        ).order_by('shift_date')

        return queryset

    def get_summary_earnings(self):
        summary_earnings = sum([
            workshift.hall_admin_earnings.final_earnings
            if workshift.hall_admin == self.employee
            else workshift.cashier_earnings.final_earnings
            for workshift in self.object_list
        ])

        return round(summary_earnings, 2)

    def get_summary_penalties(self):
        summary_penalties = sum([
            workshift.hall_admin_penalty
            if workshift.hall_admin == self.employee
            else workshift.cash_admin_penalty
            for workshift in self.object_list
        ])

        return round(summary_penalties, 2)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'employee': self.employee,
            'summary_earnings': self.get_summary_earnings(),
            'summary_penalties': self.get_summary_penalties(),
            'summary_shortages': self.object_list.filter(
                cash_admin=self.employee,
                shortage_paid=False,
            ).aggregate(Sum('shortage')).get('shortage__sum')
        })
        return context


class DocumentsList(LoginRequiredMixin, TitleMixin, TemplateView):
    template_name = 'salary/employee_documents_list.html'
    title = 'Список документов'


class AddWorkshiftData(PermissionRequiredMixin, TitleMixin, SuccessUrlMixin,
                        CreateView):
    form_class = AddWorkshiftDataForm
    permission_required = 'salary.add_workingshift'
    template_name = 'salary/add_workshift.html'
    title = 'Добавление смен'

    def dispatch(self, request: HttpRequest, *args: Any,
                 **kwargs: Any) -> HttpResponse:
        if kwargs.get('date'):
            year, month, day = (map(int, kwargs.get('date').split('-')))
            self.closed_date = datetime.date(year, month, day)
        else:
            self.closed_date = timezone.localdate(timezone.now())

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initional = super().get_initial()
        initional.update({
            'cash_admin': self.request.user,
            'shift_date': self.closed_date.strftime('%Y-%m-%d'),
        })
        logging.debug(f'[1/3] Function get_initial update fields values.')
        return initional

    def form_valid(self, form):
        object = form.save(commit=False)
        object.editor = self.request.user.get_full_name()
        object.slug = object.shift_date
        return super().form_valid(form)


class EditWorkshiftData(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                        SuccessUrlMixin, EditModelEditorFieldsMixin,
                        UpdateView):
    model = WorkingShift
    form_class = EditWorkshiftDataForm
    permission_required = 'salary.change_workingshift'
    template_name = 'salary/edit_workshift.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['start_date'] = context['object'].shift_date - relativedelta(days=1)
        return context


class ShortagePayment(WorkingshiftPermissonsMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        self.url = self.request.GET.get('next', reverse_lazy('index'))
        workshift = get_object_or_404(WorkingShift, slug=kwargs.get('slug'))
        workshift.shortage_paid = True
        workshift.save()
        return super().get_redirect_url(*args, **kwargs)


class StaffEditWorkshift(EditWorkshiftData, WorkingshiftPermissonsMixin):
    form_class = StaffEditWorkshiftForm


class ResetPasswordView(TitleMixin, PasswordResetView):
    title = 'Сброс пароля'
    template_name = 'salary/auth/password_reset_form.html'
    email_template_name = 'salary/auth/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


class ResetPasswordMailed(TitleMixin, PasswordResetDoneView):
    template_name = 'salary/auth/password_reset_done.html'
    title = 'Пароль успешно сброшен'


class ResetPasswordConfirmView(TitleMixin, PasswordResetConfirmView):
    template_name = 'salary/auth/password_reset_confirm.html'
    title = 'Форма сброса пароля'
    success_url = reverse_lazy('login')


class EmploymentDocumentsView(EmployeePermissionsMixin, TitleMixin,
                              TemplateView):
    title = 'Документы по трудоустройству'
    template_name = 'salary/documents_view/documents_list.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.employee = get_object_or_404(
            User, username=self.kwargs.get('user')
        )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'files_list': get_employee_documents_urls(self.employee),
            'employee': self.employee,
        })

        return context


class EmploymentDocumentsUploadView(LoginRequiredMixin, TitleMixin, TemplateView):
    title = 'Загрузка документов'
    template_name = 'salary/documents_view/documents_upload.html'

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        employment_files = request.FILES.getlist('files')

        if employment_files:
            for file in employment_files:
                document_file_handler(request.user, file)

        return render(
            request, 
            self.template_name, 
            context={'message': 'Файлы успешно загружены. Ожидайте проверку руководством.'},
        )


class UnverifiedEmployeeView(LoginRequiredMixin, TitleMixin, TemplateView):
    title = 'Главная'
    template_name = 'salary/unverified_employee.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        true_status = Profile.ProfileStatus.VERIFIED
        if (request.user.is_authenticated
            and request.user.profile.profile_status == true_status):
                return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unclosed_shifts_dates = get_employee_unclosed_workshifts_dates(
            user_id=self.request.user.id
        )
        context.update({ 'unclosed_shifts_dates': unclosed_shifts_dates })
        return context


class DocumentDeleteView(EmployeePermissionsMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        self.url = self.request.GET.get('next', reverse_lazy('index'))
        employee = get_object_or_404(User, pk=self.kwargs.get('pk', 0))
        
        filename = self.kwargs.get('filename')
        if filename:
            delete_document_from_storage(employee, filename)

        return super().get_redirect_url(*args, **kwargs)


class ProfileAuthenticationView(EmployeePermissionsMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        self.url = self.request.GET.get('next', reverse_lazy('index'))
        employee = get_object_or_404(User, pk=self.kwargs.get('pk', 0))
        employee.profile.profile_status = Profile.ProfileStatus.AUTHENTICATED
        authentification_user(request=self.request, user=employee)

        return super().get_redirect_url(*args, **kwargs)


class ProfileStatusApprovalView(EmployeePermissionsMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        self.url = self.request.GET.get('next', reverse_lazy('index'))
        employee = get_object_or_404(User, pk=self.kwargs.get('pk', 0))
        employee.profile.profile_status = Profile.ProfileStatus.VERIFIED
        chat_permission = Permission.objects.get(name='Can create new chats')
        employee.user_permissions.add(chat_permission)
        employee.save()

        return super().get_redirect_url(*args, **kwargs)


class MessengerMainView(LoginRequiredMixin, TitleMixin ,TemplateView):
    template_name = 'salary/chat/main_window.html'
    title = 'Чат'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data.update({
            'active_users': get_acvite_users_list(self.request.user.id),
            'chats_list': get_chats_list(self.request.user.id),
        })
        return context_data

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(add_message_and_return_chat(request))


class MessengerChatView(MessengerMainView):
    template_name = 'salary/chat/chat_open.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        selected_chat_slug = self.kwargs.get('slug')
        self.chat_object = get_object_or_404(Chat, slug=selected_chat_slug)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        messages_list = []
        messages_list = get_messages_list(self.chat_object.slug)

        chats_list = get_chats_list(
            self.request.user.id,
            self.chat_object.slug
        )
        recipient = get_chat_info(
            self.chat_object,
            self.request.user.id
        ).member

        mark_messages_as_read(messages_list, self.request.user)
        context.update({
            'chats_list': chats_list,
            'messages_list': messages_list,
            'recipient': recipient,
        })

        return context


class MessengerNewChatView(MessengerMainView):
    template_name = 'salary/chat/chat_open.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.recipient = get_object_or_404(User, pk=self.kwargs.get('pk'))
        chat = members_chat_exists(request.user, self.recipient)
        if chat:
            return redirect(chat)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            { 'recipient': self.recipient }
        )

        return context


class CalendarView(LoginRequiredMixin, MonthYearExtractMixin,
                   TitleMixin, TemplateView):
    template_name: str = 'salary/calendar/calendar.html'
    title: str = 'График смен'
    
    def dispatch(self, request: HttpRequest,
                 *args: Any, **kwargs: Any) -> HttpResponse:
        if self.kwargs.get('pk'):
            self.requested_user = get_object_or_404(
                User, pk=self.kwargs.get('pk')
            )
        else:
            self.requested_user = self.request.user

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        context: dict = super().get_context_data(**kwargs)
        user_calendar = get_user_calendar(self.requested_user, self.year,
                                          self.month)

        context.update({
            'month_calendar': user_calendar,
            'requested_date': datetime.date(self.year, self.month, 1),
            'requested_user': self.requested_user,
        })
        return context


class StaffCalendarView(StaffOnlyMixin, CalendarView):
    pass


class StaffCalendarListView(TitleMixin, ListView):
    model = User
    queryset = User.objects.filter(is_active=True).exclude(
        is_staff=True).exclude(profile__position=4).select_related(
                'profile', 'profile__position').order_by('-profile__position')

    template_name: str = 'salary/calendar/calendar_users_list.html'
    title = 'Графики пользователей'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            'date': datetime.date.today()
        })
        return context


class AwardRatingView(MonthlyReportListView):
    template_name: str = 'salary/award_rating.html'
    title = 'Рейтинговый отчёт'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            'award_data': get_awards_data(month=self.month, year=self.year),
            'current_date': datetime.date(self.year, self.month, 1),
            'minimal_workshifts_number': settings.MINIMAL_WORKSHIFTS_NUMBER,
            'avg_bar_criteria': settings.AVERAGE_BAR_REVENUE_CRITERIA,
            'avg_hookah_criteria': settings.AVERAGE_HOOKAH_REVENUE_CRITERIA
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


@login_required
def user_session_set(request, user_id):
    """
    Set user session for superuser.
    """
    if request.user.is_superuser:
        requested_user = get_object_or_404(User, pk=user_id)
        login(request, requested_user)
        return redirect(reverse_lazy('index'))
    raise PermissionDenied
