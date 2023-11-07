from django.contrib import admin

from .models import *


class WorkshiftAdmin(admin.ModelAdmin):
    list_display = ('shift_date', 'hall_admin', 'cash_admin', 'status')
    list_display_links = ('shift_date',)
    search_fields = ('shift_date',)
    list_filter = ('status',)


class DisciplinaryRegAdmin(admin.ModelAdmin):
    list_display = ('article', 'title', 'sanction')


class DeleteNotAllowedModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Profile, DeleteNotAllowedModelAdmin)
admin.site.register(WorkingShift, WorkshiftAdmin)
admin.site.register(Position, DeleteNotAllowedModelAdmin)
admin.site.register(DisciplinaryRegulations, DisciplinaryRegAdmin)
admin.site.register(Misconduct)