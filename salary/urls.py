from django.urls import path

from .views import *


urlpatterns = [
    path('login/', LoginUser.as_view(), name='login'),
    path('registration/', RegistrationUser.as_view(), name='registration'),
    path('', IndexEmployeeView.as_view(), name='index'),
    path('logout/', logout_user, name='logout'),
    path('add_workshift/', AddWorkshiftData.as_view(), name='add_workshift'),
    path('add_workshift/<str:date>/', AddWorkshiftData.as_view(), name='add_workshift_for_date'),
    path('edit_workshift/<slug:slug>/', EditWorkshiftData.as_view(), name='edit_workshift'),
    path('staff_edit_workshift/<slug:slug>/', StaffEditWorkshift.as_view(), name='staff_edit_workshift'),
    path('delete_workshift/<slug:slug>/', DeleteWorkshift.as_view(), name='delete_workshift'),
    path('detail/<slug:slug>/', WorkshiftDetailView.as_view(), name='detail_workshift'),
    path('monthly_report/<int:year>/<int:month>/', MonthlyReportListView.as_view(), name='monthly_report'),
    path('reports_list/', ReportsView.as_view(), name='reports_list'),
    path('users_view/', AdminUserView.as_view(), name='user_view'),
    path('users_view/<str:all>/', AdminUserView.as_view(), name='user_view_all'),
    path('user_edit/<int:pk>/', StaffEditUser.as_view(), name='staff_user_edit'),
    path('staff_index/', StaffIndexView.as_view(), name='staff_index'),
    path('workshifts_view/', StaffWorkshiftsView.as_view(), name='workshifts_view'),
    path('workshifts_archive_view/<int:year>/<int:month>/', StaffArchiveWorkshiftsView.as_view(), name='workshift_archive_view'),
    path('workshifts_months/', StaffWorkshiftsMonthlyList.as_view(), name='workshifts_months'),
    path('dismissal/<int:pk>/', DismissalEmployee.as_view(), name='dismissal_user'),
    path('show_user_detail/', ShowUserProfile.as_view(), name='show_user_detail'),
    path('edit_profile/', EditUser.as_view(), name='profile_edit'),
    path('add_misconduct/', AddMisconductView.as_view(), name='add_misconduct'),
    path('misconducts/', MisconductListView.as_view(), name='misconducts_view'),
    path('misconducts/<str:username>/', MisconductUserView.as_view(), name='misconducts_user_view'),
    path('edit_misconduct/<int:pk>/', MisconductUpdateView.as_view(), name='edit_misconduct'),
    path('delete_misconduct/<int:pk>/', MisconductDeleteView.as_view(), name='delete_misconduct'),
    path('misconduct_detail/<slug:slug>/', MisconductDetailView.as_view(), name='misconduct_detail'),
    path('load_regulation_data/', load_regulation_data, name='load_regulation_data'),
    path('my_workshifts/', EmployeeWorkshiftsView.as_view(), name='employee_workshifts'),
    path('monthly_list/', EmployeeMonthlyListView.as_view(), name='employee_monthly_list'),
    path('workshifts_view/<int:year>/<int:month>/', EmployeeWorkshiftsView.as_view(), name='employee_archive_view'),
    path('documents/', DocumentsList.as_view(), name='employee_documents'),
    path('workshifts_view/<int:year>/<int:month>/<int:employee>/', StaffEmployeeMonthView.as_view(), name='staff_employee_month_view'),
    path('password_change/', EmployeePasswordChangeView.as_view(), name='passowrd_change'),
    path('password_change/<str:user>/', StaffPasswordChangeView.as_view(), name='staff_passowrd_change'),
    path('password_reset/', ResetPasswordView.as_view(), name='password_reset'),
    path('password_reset_done/', ResetPasswordMailed.as_view(), name='password_reset_done'),
    path('password_reset/<uidb64>/<token>/', ResetPasswordConfirmView.as_view(), name='password_reset_confirm'),
    path('monthly_analytics/<int:year>/<int:month>/', MonthlyAnalyticalReport.as_view(), name='monthly_analytics'),
    path('analytics_reports/', AnalyticalView.as_view(), name='analytics_reports'),
    path('confirm_user_mail/<uidb64>/<token>/', ConfirmUserView.as_view(), name='confirm_user_mail'),
    path('confirm_mail_status/', ConfirmMailStatus.as_view(), name='confirm_mail_status'),
    path('request_confirmation_link/', request_confirmation_link, name='request_confirmation_link'),
    path('shortage_payment/<slug:slug>/', ShortagePayment.as_view(), name='shortage_payment'),
    path('employment_documents_view/<str:user>/', EmploymentDocumentsView.as_view(), name='employment_documents_view'),
    path('employment_documents_upload/', EmploymentDocumentsUploadView.as_view(), name='employment_documents_upload'),
    path('pending_verification/', UnverifiedEmployeeView.as_view(), name='pending_verification'),
    path('document_delete/<int:pk>/<str:filename>/', DocumentDeleteView.as_view(), name='document_delete'),
    path('profile_approval/<int:pk>/', ProfileStatusApprovalView.as_view(), name='profile_approval'),
    path('messenger/', MessengerMainView.as_view(), name='messenger'),
    path('messenger/<slug:slug>/', MessengerChatView.as_view(), name='messenger_open_chat'),
    path('messenger/new_chat/<int:pk>/', MessengerNewChatView.as_view(), name='messenger_new_chat'),
    path('calendar/<int:year>/<int:month>/', CalendarView.as_view(), name='calendar'),
    path('staff_schedule_list/', StaffCalendarListView.as_view(), name='staff_schedule_list'),
    path('staff_calendar/<int:pk>/<int:year>/<int:month>/', StaffCalendarView.as_view(), name='staff_calendar'),
    path('authentication/<int:pk>/', ProfileAuthenticationView.as_view(), name='authentication'),
    path('award_rating/<int:year>/<int:month>/', AwardRatingView.as_view(), name='award_rating'),
    path('user_session_set/<int:user_id>/', user_session_set, name='session_set'),
    path('everyday_report/', EverydayReportView.as_view(), name='everyday_report'),
    path('costs_and_errors_form/', AddCostErrorFormView.as_view(), name='costs_and_errors_form'),
    path('add_kna_error/', CreateErrorRedirectView.as_view(), name='add_kna_error'),
    path('add_cost_to_report/', CreateCostRedirectView.as_view(), name='add_cost_to_report'),
    path('del_cost_from_report/<int:pk>/', CostDeleteView.as_view(), name='del_cost_from_report'),
    path('del_error_from_report/<int:pk>/', ErrorDeleteView.as_view(), name='del_error_from_report'),
    path('update_cost_in_report/<int:pk>/', CostUpdateView.as_view(), name='update_cost_in_report'),
    path('update_error_in_report/<int:pk>/', ErrorUpdateView.as_view(), name='update_error_in_report'),
]