from django.http import request
from django.urls import path

from .views import *


urlpatterns = [
    path('login/', LoginUser.as_view(), name='login'),
    path('registration/', registration, name='registration'),
    path('', IndexView.as_view(), name='index'),
    path('logout/', logout_user, name='logout'),
    path('add_workshift/', AddWorkshiftData.as_view(), name='add_workshift'),
    path('edit_workshift/<int:pk>/', EditWorkshiftData.as_view(), name='edit_workshift'),
]