from django.urls import path

from .views import *


urlpatterns = [
    path('login/', LoginUser.as_view(), name='login'),
    path('registration/', registration, name='registration'),
    path('', IndexView.as_view(), name='index'),
    path('logout/', logout_user, name='logout'),
]