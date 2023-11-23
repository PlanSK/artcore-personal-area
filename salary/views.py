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
from django.views.generic.edit import CreateView, DeleteView, UpdateView, FormView
from django.views.generic.base import RedirectView
from django.db.models import Q, QuerySet, Sum, Avg

from .forms import *
from .mixins import *
from salary.services.chat import *
from salary.services.shift_calendar import (get_user_calendar,
                                            get_employees_at_work)
from salary.services.misconduct import Intruder
from salary.services.internal_model_func import get_misconduct_slug
from salary.services.workshift import (
    notification_of_upcoming_shifts, get_missed_dates_tuple,
    get_employee_workshift_indicators, get_employee_month_workshifts,
    get_employee_unclosed_workshifts_dates, get_unclosed_workshift_number,
    get_summary_workshift_data
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
from salary.services.misconduct import (
    get_misconduct_employee_data, get_sorted_intruders_list, get_penalty_sum
)
from salary.services.profile_services import get_birthday_person_list
from salary.services.analytic import get_analytic_data


WORKINGSHIFT_PERMISSONS_TUPLE: tuple[str, ...] = (
    'salary.view_workingshift',
    'salary.add_workingshift',
    'salary.change_workingshift',
    'salary.delete_workingshift',
    'salary.view_workshift_report',
    'salary.advanced_change_workshift',
)


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
        template_for_render = self.template_name
        if user_form.is_valid() and profile_form.is_valid():
            user = registration_user(
                request=request,
                user_form=user_form,
                profile_form=profile_form
            )
            context = { 'first_name': user.first_name }
            template_for_render = self.success_template_name
        else:
            context = self.get_context_data(
                profile_form=profile_form,
                user_form=user_form
            )

        return render(request, template_for_render, context=context)


def request_confirmation_link(request):
    username = request.POST.get('user')
    sending_confirmation_link(request=request, username=username)

    return HttpResponse('Success sent.')


class ConfirmUserView(TitleMixin, SuccessUrlMixin, UpdateContextMixin,
                      TemplateView):
    template_name = 'salary/auth/email_confirmed.html'
    title = 'Учетная запись активирована'

    def dispatch(self, request, *args: Any, **kwargs: Any):
        user_uidb64: str = kwargs.get('uidb64') # type: ignore
        request_token: str = kwargs.get('token') # type: ignore

        confirmation_user_email(
            request=request,
            user_uidb64_str=user_uidb64,
            request_token=request_token
        )
        self.requested_user = get_user_instance_from_uidb64(
            uidb64_str=user_uidb64
        )
        return super().dispatch(request, *args, **kwargs)

    def get_additional_context_data(self) -> dict:
        return {'first_name': self.requested_user.first_name}


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


class AdminUserView(EmployeePermissionsMixin, TitleMixin, UpdateContextMixin,
                    ListView):
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

    def get_additional_context_data(self) -> dict:
        return {
            'attestation_enabled': settings.ATTESTATION_ENABLED,
            'only_actived': True if not self.kwargs.get('all') else False
        }


class StaffIndexView(PermissionRequiredMixin, TitleMixin, UpdateContextMixin,
                     TemplateView, CatchingExceptionsMixin):
    template_name = 'salary/staff/staff_index.html'
    title = 'Главная'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_additional_context_data(self) -> dict:
        employees_at_work = get_employees_at_work()
        today_date = timezone.localdate(timezone.now())
        birthday_person_list = get_birthday_person_list(day=today_date.day,
                                                        month=today_date.month)
        additional_context_data = {
            'employees_at_work': employees_at_work,
            'today_date': today_date,
            'missed_workshifts_dates': get_missed_dates_tuple(),
            'birthday_person_list': birthday_person_list,
            'unread_messages_number': get_unread_messages_number(
                self.request.user),
            'unclosed_workshifts': get_unclosed_workshift_number(),
            'total_rating_data': get_filtered_rating_data(today_date.month,
                                                          today_date.year)
        }
        return additional_context_data


class StaffWorkshiftsView(PermissionRequiredMixin, MonthYearExtractMixin,
                          TitleMixin, UpdateContextMixin, ListView):
    template_name = 'salary/staff_workshifts_view.html'
    model = WorkingShift
    title = 'Смены'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_queryset(self):
        workshifts = WorkingShift.objects.select_related('hall_admin',
                                                         'cash_admin')
        return workshifts

    def get_additional_context_data(self) -> dict:
        additional_context_data = {
            'workshift_list': self.object_list.exclude(
                status=WorkingShift.WorkshiftStatus.VERIFIED),
            'is_unverified': True,
            'missed_workshifts_dates': get_missed_dates_tuple(),
            'workshift_dates': timezone.now().date(),
        }
        return additional_context_data


class StaffArchiveWorkshiftsView(PermissionRequiredMixin,
                                 MonthYearExtractMixin, TitleMixin,
                                 UpdateContextMixin, ListView):
    template_name = 'salary/staff_workshifts_view.html'
    model = WorkingShift
    title = 'Смены'
    context_object_name = 'workshift_list'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_queryset(self):
        if self.kwargs.get('year') and self.kwargs.get('month'):
            queryset = WorkingShift.objects.filter(
                shift_date__month = self.month,
                shift_date__year = self.year
            ).select_related('cash_admin', 'hall_admin').order_by('shift_date')
        else:
            HttpResponseNotFound('No all data found.')
        return queryset

    def get_additional_context_data(self) -> dict:
        additional_context_data = {
            'summary_revenue': sum([
                workshift.summary_revenue
                for workshift in self.object_list
            ]),
            'workshift_dates': datetime.date(self.year, self.month, 1), # type:ignore
            'is_unverified': False,
            'missed_workshifts_dates': get_missed_dates_tuple(),
        }
        return additional_context_data


class StaffWorkshiftsForYearView(PermissionRequiredMixin, TitleMixin,
                                 MonthYearExtractMixin, UpdateContextMixin,
                                 ListView):
    template_name = 'salary/staff_months_workshifts_list.html'
    model = WorkingShift
    title = 'Смены'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_queryset(self):
        workshifts_months = WorkingShift.objects.filter(
            shift_date__year=self.year).dates('shift_date', 'month')
        return workshifts_months

    def get_additional_context_data(self) -> dict:
        return {'year': self.year}


class StaffWorkshiftsYearView(PermissionRequiredMixin, TitleMixin, ListView):
    template_name = 'salary/staff_years_workshifts_list.html'
    model = WorkingShift
    title = 'Смены'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_queryset(self):
        workshifts_years = WorkingShift.objects.dates('shift_date', 'year')
        return workshifts_years


class AllYearsReportsView(StaffWorkshiftsYearView):
    template_name = 'salary/month_reports/all_years_reports_list.html'
    title = 'Ежемесячные отчёты'


class AllYearsAnalyticView(StaffWorkshiftsYearView):
    template_name = 'salary/month_reports/all_years_analytic_list.html'
    title = 'Аналитика'


class MonthReportsForYearView(StaffWorkshiftsForYearView):
    template_name = 'salary/month_reports/month_reports_for_year.html'
    title = 'Ежемесячные отчёты'


class AnalyticForYearView(StaffWorkshiftsForYearView):
    template_name = 'salary/month_reports/analytic_for_year.html'
    title = 'Аналитика'


class DeleteWorkshift(PermissionRequiredMixin, TitleMixin, SuccessUrlMixin,
                      DeleteView):
    model = WorkingShift
    title = 'Удаление смены'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE


class MonthlyReportListView(PermissionRequiredMixin, MonthYearExtractMixin,
                            TitleMixin, UpdateContextMixin, TemplateView):
    template_name = 'salary/month_reports/monthlyreport_list.html'
    title = 'Зарплатный отчёт'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_additional_context_data(self):
        monthly_report_data = get_monthly_report(
            month=self.month,
            year=self.year
        )
        current_date = datetime.date(self.year, self.month, 1)
        additional_context_data = {
            'report_data': monthly_report_data,
            'current_date': current_date,
        }
        return additional_context_data


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


class MisconductListView(MisconductPermissionsMixin, TitleMixin,
                         UpdateContextMixin, ListView):
    model = Misconduct
    title = 'Список нарушителей'
    template_name = 'salary/intruders_list.html'
    is_show_dissmissed = False

    def get_queryset(self) -> List[Intruder]:
        queryset = Misconduct.objects.select_related('intruder__profile')
        if not self.request.GET.get('show_dissmissed'):
            self.is_show_dissmissed = True
            dismissed_status = Profile.ProfileStatus.DISMISSED
            return queryset.exclude(
                intruder__profile__profile_status=dismissed_status)
        return queryset

    def get_additional_context_data(self):
        additional_context_data = {
            'intruders_list': get_sorted_intruders_list(self.object_list),
            'is_show_dissmissed': self.is_show_dissmissed,
        }
        return additional_context_data


class MisconductUserView(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                         UpdateContextMixin, TitleMixin, ListView):
    model = Misconduct
    title = 'Нарушения'
    permission_required = 'salary.view_misconduct'

    def dispatch(self, request, *args: Any, **kwargs: Any):
        self.intruder = self.kwargs.get('username')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Misconduct.objects.filter(
            intruder__username=self.intruder).select_related(
                'intruder', 'regulations_article'
            )

    def get_additional_context_data(self) -> dict:
        additional_context_data = {
            'intruder': get_object_or_404(User, username=self.intruder),
            'penalty_sum': get_penalty_sum(self.object_list),
        }
        return additional_context_data


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

# TODO: Need to refactoring this
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


class ShowUserProfile(LoginRequiredMixin, TitleMixin, UpdateContextMixin,
                      DetailView):
    model = User
    title = 'Просмотр профиля'
    queryset = User.objects.select_related('profile')
    template_name = 'salary/user_detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            queryset if queryset else self.get_queryset(),
            pk=self.request.user.pk
        )

    def get_additional_context_data(self) -> dict:
        return {
            'attestation_enabled': settings.ATTESTATION_ENABLED
        }


class WorkshiftDetailView(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                          UpdateContextMixin, TitleMixin, DetailView):
    model = WorkingShift
    template_name = 'salary/reports/workingshift_detail.html'
    title = 'Детальный просмотр смены'
    permission_required = 'salary.view_workingshift'
    queryset = WorkingShift.objects.select_related(
            'cash_admin__profile__position',
            'hall_admin__profile__position',
    )
    context_object_name = 'workshift'

    def get_additional_context_data(self) -> dict:
        workshift_object = self.get_object()
        yesterday = workshift_object.shift_date - datetime.timedelta(days=1)
        additional_context_data = {
            'yesterday': yesterday,
            'attestation_enabled': settings.ATTESTATION_ENABLED,
            'publication_enabled': settings.PUBLICATION_ENABLED
        }
        return additional_context_data


class MisconductDetailView(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                            TitleMixin, DetailView):
    model = Misconduct
    title = 'Протокол нарушения'
    permission_required = 'salary.view_misconduct'
    context_object_name = 'misconduct'
    queryset = Misconduct.objects.select_related('intruder', 'moderator',
                                                 'regulations_article')


class MonthlyAnalyticalReport(PermissionRequiredMixin,
                              MonthYearExtractMixin, TitleMixin,
                              UpdateContextMixin, TemplateView):
    title = 'Аналитический отчёт'
    template_name = 'salary/month_reports/monthly_analytical_report.html'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_additional_context_data(self) -> dict:
        analytic_data = get_analytic_data(self.month, self.year)
        return {'analytic_data': analytic_data}


class IndexEmployeeView(LoginRequiredMixin, ProfileStatusRedirectMixin,
                        TitleMixin, UpdateContextMixin, TemplateView,
                        CatchingExceptionsMixin):
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

    def get_additional_context_data(self) -> dict:
        logger.debug(f'Get user {self.request.user.username} context data.')
        notification_about_shift = notification_of_upcoming_shifts(
            user_id=self.request.user.pk)
        misconduct_data = get_misconduct_employee_data(self.request.user.id)
        employee_month_indicators = get_employee_workshift_indicators(
            self.request.user.id)
        unclosed_shifts_dates = get_employee_unclosed_workshifts_dates(
            self.request.user.id)
        logger.debug(
            f'Shifts to close number: {len(unclosed_shifts_dates)}. '
            f'Notofication: {notification_about_shift}.'
        )
        additional_context_data = {
            'employee_indicators': employee_month_indicators,
            'misconduct_data': misconduct_data,
            'today_date': timezone.localdate(timezone.now()),
            'unclosed_shifts_dates': unclosed_shifts_dates,
            'notification_about_shift': notification_about_shift,
            'minimal_workshifts_number': settings.MINIMAL_WORKSHIFTS_NUMBER
        }
        logger.debug('Context data is updated. Return context.')
        return additional_context_data


class EmployeeWorkshiftsView(PermissionRequiredMixin, MonthYearExtractMixin,
                             TitleMixin, UpdateContextMixin, TemplateView):
    template_name = 'salary/employee_workshifts_view.html'
    title = 'Смены'
    permission_required = 'salary.view_workingshift'

    def get_additional_context_data(self) -> dict:
        workshifts_list = get_employee_month_workshifts(
            self.request.user.id, self.month, self.year)
        employee_month_indicators = get_employee_workshift_indicators(
            self.request.user.id, self.month, self.year)
        return {
            'employee_indicators': employee_month_indicators,
            'workshifts_list': workshifts_list
        }


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


class StaffEmployeeMonthView(PermissionRequiredMixin,
                             MonthYearExtractMixin, TitleMixin,
                             UpdateContextMixin, ListView):
    template_name = 'salary/staff_employee_month_view.html'
    title = 'Просмотр смен'
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def dispatch(self, request, *args: Any, **kwargs: Any):
        self.employee = get_object_or_404(User, pk=self.kwargs.get('employee'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        return get_employee_month_workshifts(
            self.employee.pk, self.month, self.year)

    def get_additional_context_data(self) -> dict:
        workshift_summary_data = get_summary_workshift_data(self.object_list,
                                                            self.employee.pk)
        additional_context_data = {
            'employee': self.employee,
            'summary_earnings': workshift_summary_data.summary_earnings,
            'summary_penalties': workshift_summary_data.summary_penalties,
            'summary_shortages': workshift_summary_data.summary_shortages
        }
        return additional_context_data


class DocumentsList(LoginRequiredMixin, TitleMixin, TemplateView):
    template_name = 'salary/employee_documents_list.html'
    title = 'Список документов'


class AddWorkshiftData(PermissionRequiredMixin, TitleMixin, CreateView):
    form_class = AddWorkshiftDataForm
    permission_required = 'salary.add_workingshift'
    template_name = 'salary/add_workshift.html'
    title = 'Добавление смен'

    def dispatch(self, request: HttpRequest, *args: Any,
                 **kwargs: Any) -> HttpResponse:
        closing_date_str: str = kwargs.get('date') # type: ignore
        if closing_date_str:
            year, month, day = (map(int, closing_date_str.split('-')))
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
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('costs_and_errors_form',
                            kwargs={'pk': self.object.pk})


class EditWorkshiftData(ProfileStatusRedirectMixin, PermissionRequiredMixin,
                        SuccessUrlMixin, EditModelEditorFieldsMixin,
                        UpdateContextMixin, UpdateView):
    model = WorkingShift
    form_class = EditWorkshiftDataForm
    permission_required: tuple[str, ...] = 'salary.change_workingshift',
    template_name = 'salary/edit_workshift.html'

    def get_additional_context_data(self) -> dict:
        workshift_object = self.get_object()
        return {
            'start_date': workshift_object.shift_date - relativedelta(days=1)
        }


class ShortagePayment(PermissionRequiredMixin, RedirectView):
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE

    def get_redirect_url(self, *args, **kwargs):
        self.url = self.request.GET.get('next', reverse_lazy('index'))
        workshift = get_object_or_404(WorkingShift, slug=kwargs.get('slug'))
        workshift.shortage_paid = True
        workshift.save()
        return super().get_redirect_url(*args, **kwargs)


class StaffEditWorkshift(EditWorkshiftData):
    form_class = StaffEditWorkshiftForm
    permission_required = WORKINGSHIFT_PERMISSONS_TUPLE


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
                              UpdateContextMixin, TemplateView):
    title = 'Документы по трудоустройству'
    template_name = 'salary/documents_view/documents_list.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.employee = get_object_or_404(
            User, username=self.kwargs.get('user')
        )

        return super().dispatch(request, *args, **kwargs)

    def get_additional_context_data(self) -> dict:
        return {
            'files_list': get_employee_documents_urls(self.employee),
            'employee': self.employee,
        }


class EmploymentDocumentsUploadView(LoginRequiredMixin, SuccessUrlMixin,
                                    UpdateContextMixin, TitleMixin,
                                    TemplateView):
    title = 'Загрузка документов'
    template_name = 'salary/documents_view/documents_upload.html'

    def dispatch(self, request: HttpRequest,
                 *args: Any, **kwargs: Any) -> HttpResponse:
        if kwargs.get('user'):
            self.target_user = get_object_or_404(
                User,
                username=self.kwargs.get('user')
            )
        else:
            self.target_user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_additional_context_data(self) -> dict:
        return {'success_url': self.get_success_url()}

    def post(self, request: HttpRequest,
             *args: Any, **kwargs: Any) -> HttpResponse:
        employment_files = request.FILES.getlist('files')
        if employment_files:
            for file in employment_files:
                document_file_handler(self.target_user, file)
        success_message = """
        Файлы успешно загружены. Ожидайте проверку руководством.
        """
        return render(
            request, 
            self.template_name, 
            context={
                'message': success_message,
                'success_url': self.get_success_url()
            },
        )


class StaffDocumentsUploadView(StaffOnlyMixin, EmploymentDocumentsUploadView):
    pass


class UnverifiedEmployeeView(LoginRequiredMixin, TitleMixin,
                             UpdateContextMixin, TemplateView):
    title = 'Главная'
    template_name = 'salary/unverified_employee.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        true_status = Profile.ProfileStatus.VERIFIED
        if (request.user.is_authenticated
            and request.user.profile.profile_status == true_status):
                return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_additional_context_data(self) -> dict:
        unclosed_shifts_dates = get_employee_unclosed_workshifts_dates(
            user_id=self.request.user.id
        )
        return { 'unclosed_shifts_dates': unclosed_shifts_dates }


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


class MessengerMainView(LoginRequiredMixin, TitleMixin, UpdateContextMixin,
                        TemplateView):
    template_name = 'salary/chat/main_window.html'
    title = 'Чат'

    def get_additional_context_data(self) -> dict:
        additional_context_data = {
            'active_users': get_acvite_users_list(self.request.user.id),
            'chats_list': get_chats_list(self.request.user.id),
        }
        return additional_context_data

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(add_message_and_return_chat(request))


class MessengerChatView(MessengerMainView):
    template_name = 'salary/chat/chat_open.html'

    def dispatch(self, request: HttpRequest,
                 *args: Any, **kwargs: Any) -> HttpResponse:
        selected_chat_slug = self.kwargs.get('slug')
        self.chat_object = get_object_or_404(Chat, slug=selected_chat_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_additional_context_data(self) -> dict:
        messages_list = []
        messages_list = get_messages_list(self.chat_object.slug)

        chats_list = get_chats_list(
            self.request.user.id,
            self.chat_object.slug
        )
        recipient = get_chat_info(
            self.chat_object, # type: ignore
            self.request.user.id
        ).member

        mark_messages_as_read(messages_list, self.request.user)
        additional_context_data = {
            'chats_list': chats_list,
            'messages_list': messages_list,
            'recipient': recipient,
        }

        return additional_context_data


class MessengerNewChatView(MessengerMainView):
    template_name = 'salary/chat/chat_open.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.recipient = get_object_or_404(User, pk=self.kwargs.get('pk'))
        chat = members_chat_exists(request.user, self.recipient)
        if chat:
            return redirect(chat)

        return super().dispatch(request, *args, **kwargs)

    def get_additional_context_data(self) -> dict:
        return {'recipient': self.recipient}


class CalendarView(LoginRequiredMixin, MonthYearExtractMixin,
                   TitleMixin, UpdateContextMixin, TemplateView):
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

    def get_additional_context_data(self) -> dict:
        user_calendar = get_user_calendar(
            self.requested_user.id, self.year, self.month)
        additional_context_data = {
            'month_calendar': user_calendar,
            'requested_date': datetime.date(self.year, self.month, 1),
            'requested_user': self.requested_user,
        }
        return additional_context_data


class StaffCalendarView(StaffOnlyMixin, CalendarView):
    pass


class StaffCalendarListView(TitleMixin, UpdateContextMixin, ListView):
    model = User
    queryset = User.objects.filter(is_active=True).exclude(
        is_staff=True).exclude(profile__position=4).select_related(
                'profile', 'profile__position').order_by('-profile__position')
    template_name: str = 'salary/calendar/calendar_users_list.html'
    title = 'Графики пользователей'

    def get_additional_context_data(self) -> dict:
        return {'date': datetime.date.today()}


class AwardRatingView(MonthlyReportListView):
    template_name: str = 'salary/month_reports/award_rating.html'
    title = 'Рейтинговый отчёт'

    def get_additional_context_data(self):
        return {
            'award_data': get_awards_data(month=self.month, year=self.year),
            'current_date': datetime.date(self.year, self.month, 1),
            'minimal_workshifts_number': settings.MINIMAL_WORKSHIFTS_NUMBER,
            'avg_bar_criteria': settings.AVERAGE_BAR_REVENUE_CRITERIA,
            'avg_hookah_criteria': settings.AVERAGE_HOOKAH_REVENUE_CRITERIA
        }


class EverydayReportPrintView(PermissionRequiredMixin, TitleMixin,
                              UpdateContextMixin, DetailView):
    template_name: str = 'salary/reports/everyday_report_print.html'
    permission_required = 'salary.change_workingshift'
    title = 'Ежедневный отчет'
    model = WorkingShift
    context_object_name = 'workshift'

    def get_additional_context_data(self) -> dict:
        errors_queryset = self.object.errors.all()
        grill_queryset = errors_queryset.filter(
            error_type=ErrorKNA.ErrorType.GRILL)
        grill_sum = grill_queryset.aggregate(
                Sum('error_sum'))
        lotto_queryset = errors_queryset.filter(
            error_type=ErrorKNA.ErrorType.LOTTO)
        lotto_sum = lotto_queryset.aggregate(
                Sum('error_sum'))
        kna_errors_queryset = errors_queryset.filter(
            error_type=ErrorKNA.ErrorType.KNA)
        additional_context_data = {
            'lotto_queryset': lotto_queryset,
            'grill_queryset': grill_queryset,
            'kna_errors_queryset': kna_errors_queryset,
            'grill_sum': grill_sum.get('error_sum__sum'),
            'lotto_sum': lotto_sum.get('error_sum__sum'),
            'yesterday': self.object.shift_date - datetime.timedelta(days=1),
        }
        return additional_context_data


class AddCostErrorFormView(PermissionRequiredMixin, TitleMixin,
                           UpdateContextMixin, TemplateView):
    template_name: str = 'salary/reports/add_costs_and_error_form.html'
    error_kna_form = ErrorKNAForm
    cost_form = CostForm
    cabinerror_form = CabinErrorForm
    permission_required = 'salary.change_workingshift'
    title = 'Добавление ошибок и расходов'

    def get_additional_context_data(self) -> dict:
        try:
            workshift = WorkingShift.objects.get(pk=self.kwargs['pk'])
        except WorkingShift.DoesNotExist:
            raise Http404
        costs = Cost.objects.filter(workshift=workshift)
        errors = ErrorKNA.objects.filter(
            workshift=workshift).order_by('error_type')
        cabin_errors_list = CabinError.objects.filter(workshift=workshift)
        additional_context_data = {
            'error_kna_form': self.error_kna_form(
                initial={'workshift': workshift}),
            'workshift_pk': workshift.pk,
            'cost_form': self.cost_form(initial={'workshift': workshift}),
            'cabinerror_form': self.cabinerror_form(
                initial={'workshift': workshift}
            ),
            'costs_list': costs,
            'errors_list': errors,
            'cabin_errors_list': cabin_errors_list,
        }
        return additional_context_data


class CreateErrorRedirectView(CreateObjectRedirectView):
    object_form = ErrorKNAForm


class CreateCostRedirectView(CreateObjectRedirectView):
    object_form = CostForm


class CreateCabinErrorRedirectView(CreateObjectRedirectView):
    object_form = CabinErrorForm


class ErrorDeleteView(SuccessUrlMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'salary.change_workingshift'
    model = ErrorKNA


class CostDeleteView(ErrorDeleteView):
    model = Cost


class CabinErrorDeleteView(ErrorDeleteView):
    model = CabinError


class CostUpdateView(SuccessUrlMixin, PermissionRequiredMixin, UpdateView):
    model = Cost
    form_class = CostForm
    permission_required = 'salary.change_workingshift'


class ErrorUpdateView(CostUpdateView):
    model = ErrorKNA
    form_class = ErrorKNAForm


class CabinErrorUpdateView(CostUpdateView):
    model = CabinError
    form_class = CabinErrorForm


@login_required
def save_workshift_and_redirect(request, pk):
    workshift = get_object_or_404(WorkingShift, pk=pk)
    if workshift.status == WorkingShift.WorkshiftStatus.NOT_CONFIRMED:
        workshift.status = WorkingShift.WorkshiftStatus.UNVERIFIED
    workshift.save()
    next_path = request.GET.get('next')
    if next_path:
        return redirect(next_path)

    return redirect(workshift)


def page_not_found(request, exception):
    response = render(request, 'salary/404.html', {'title': 'Page not found'})
    response.status_code = 404
    return response


def page_forbidden(request, exception):
    response = render(
        request, 'salary/403.html', {'title': 'Access forbidden'}
    )
    response.status_code = 403
    return response


def page_server_error(request):
    response = render(
        request, 'salary/500.html', {'title': 'Internal Server Error'}
    )
    response.status_code = 500
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
