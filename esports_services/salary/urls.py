from django.urls import path

from .views import *


urlpatterns = [
    path('login/', LoginUser.as_view(), name='login'),
    path('registration/', RegistrationUser.as_view(), name='registration'),
    path('', IndexView.as_view(), name='index'),
    path('<int:year>/<int:month>/', IndexView.as_view(), name='archive_view'),
    path('detail/<slug:slug>/', WorkshiftDetailView.as_view(), name='detail_workshift'),
    path('logout/', logout_user, name='logout'),
    path('add_workshift/', AddWorkshiftData.as_view(), name='add_workshift'),
    path('edit_workshift/<slug:slug>/', EditWorkshiftData.as_view(), name='edit_workshift'),
    path('staff_edit_workshift/<slug:slug>/', StaffEditWorkshift.as_view(), name='staff_edit_workshift'),
    path('delete_workshift/<slug:slug>/', DeleteWorkshift.as_view(), name='delete_workshift'),
    path('staff_view/<str:request_user>/<int:year>/<int:month>/', StaffUserView.as_view(), name='staff_user_view'),
    path('monthly_report/<int:year>/<int:month>/', MonthlyReportListView.as_view(), name='monthly_report'),
    path('reports_list/', ReportsView.as_view(), name='reports_list'),
    path('dashboard/', AdminView.as_view(), name='dashboard'),
    path('users_view/', AdminUserView.as_view(), name='user_view'),
    path('users_view/<str:all>/', AdminUserView.as_view(), name='user_view_all'),
    path('workshifts_view/', AdminWorkshiftsView.as_view(), name='workshifts_view'),
    path('workshifts_view/<str:all>/', AdminWorkshiftsView.as_view(), name='workshifts_view_all'),
    path('user_edit/<int:pk>/', StaffEditUser.as_view(), name='staff_user_edit'),
    path('dismissal/<int:pk>/', DismissalEmployee.as_view(), name='dismissal_user'),
    path('edit_profile/', EditUser.as_view(), name='profile_edit'),
    path('add_misconduct/', AddMisconductView.as_view(), name='add_misconduct'),
]