from django.http import request
from django.urls import path

from .views import *


urlpatterns = [
    path('login/', LoginUser.as_view(), name='login'),
    path('registration/', registration, name='registration'),
    path('', IndexView.as_view(), name='index'),
    path('<int:year>/<int:month>', IndexView.as_view(), name='archive_view'),
    path('logout/', logout_user, name='logout'),
    path('add_workshift/', AddWorkshiftData.as_view(), name='add_workshift'),
    path('edit_workshift/<slug:slug>/', EditWorkshiftData.as_view(), name='edit_workshift'),
    path('staff_edit_workshift/<slug:slug>/', StaffEditWorkshift.as_view(), name='staff_edit_workshift'),
    path('delete_workshift/<slug:slug>', DeleteWorkshift.as_view(), name='delete_workshift'),
    path('staff_view/<str:request_user>', StaffUserView.as_view(), name='staff_user_view')
]