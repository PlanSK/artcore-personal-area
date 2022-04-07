from django.urls import path

from .views import *


urlpatterns = [
    path('login/', LoginUser.as_view(), name='login'),
    path('registration/', RegistrationUser.as_view(), name='registration'),
    path('', IndexEmployeeView.as_view(), name='index'),
    path('detail/<slug:slug>/', WorkshiftDetailView.as_view(), name='detail_workshift'),
    path('logout/', logout_user, name='logout'),
    path('add_workshift/', AddWorkshiftData.as_view(), name='add_workshift'),
    path('edit_workshift/<slug:slug>/', EditWorkshiftData.as_view(), name='edit_workshift'),
    path('staff_edit_workshift/<slug:slug>/', StaffEditWorkshift.as_view(), name='staff_edit_workshift'),
    path('delete_workshift/<slug:slug>/', DeleteWorkshift.as_view(), name='delete_workshift'),
    path('monthly_report/<int:year>/<int:month>/', MonthlyReportListView.as_view(), name='monthly_report'),
    path('reports_list/', ReportsView.as_view(), name='reports_list'),
    path('users_view/', AdminUserView.as_view(), name='user_view'),
    path('users_view/<str:all>/', AdminUserView.as_view(), name='user_view_all'),
    path('workshifts_view/', StaffWorkshiftsView.as_view(), name='workshifts_view'),
    path('workshifts_archive_view/<int:year>/<int:month>/', StaffArchiveWorkshiftsView.as_view(), name='workshift_archive_view'),
    path('workshifts_months/', StaffWorkshiftsMonthlyList.as_view(), name='workshifts_months'),
    path('user_edit/<int:pk>/', StaffEditUser.as_view(), name='staff_user_edit'),
    path('dismissal/<int:pk>/', DismissalEmployee.as_view(), name='dismissal_user'),
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
    path('workshifts_view/<int:year>/<int:month>/', EmployeeArchiveView.as_view(), name='employee_archive_view'),
    path('documents/', EmployeeDocumentsList.as_view(), name='employee_documents'),
    path('workshifts_view/<int:year>/<int:month>/<str:employee>/', StaffEmployeeMonthView.as_view(), name='staff_employee_month_view'),
]