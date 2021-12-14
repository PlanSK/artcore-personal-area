from django.contrib import admin

from .models import *

admin.site.register(Employee)
admin.site.register(WorkingShift)
admin.site.register(Position)