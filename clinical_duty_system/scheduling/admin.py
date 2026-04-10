from django.contrib import admin
from .models import (
    ClinicalArea,
    DutyGroup,
    DutyGroupMembership,
    DutyHistory,
    DutySchedule,
    Notification,
    PatientCase,
)

admin.site.register(ClinicalArea)
admin.site.register(DutySchedule)
admin.site.register(PatientCase)
admin.site.register(Notification)
admin.site.register(DutyHistory)
admin.site.register(DutyGroup)
admin.site.register(DutyGroupMembership)
