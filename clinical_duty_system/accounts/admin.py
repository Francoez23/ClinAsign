from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'student_id', 'created_by', 'year_level', 'section')
    list_filter = ('role', 'year_level', 'section')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'student_id')
