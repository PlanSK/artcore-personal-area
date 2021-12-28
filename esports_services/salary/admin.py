from django.contrib import admin
import datetime

from .models import *

class WorkshiftAdmin(admin.ModelAdmin):
    list_display = ('shift_date', 'hall_admin', 'cash_admin', 'is_verified')
    list_display_links = ('shift_date',)
    search_fields = ('shift_date',)



admin.site.register(Profile)
admin.site.register(WorkingShift, WorkshiftAdmin)
admin.site.register(Position)