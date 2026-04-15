from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('classes/', views.group_list, name='group-list'),
    path('classes/<int:pk>/students/', views.group_students, name='group-students'),
    path('classes/create/', views.group_create, name='group-create'),
    path('classes/join/', views.group_join, name='group-join'),
    path('clinical-areas/', views.clinical_area_list, name='clinical-area-list'),
    path('clinical-areas/create/', views.clinical_area_create, name='clinical-area-create'),
    path('schedules/', views.schedule_list, name='schedule-list'),
    path('schedules/create/', views.schedule_create, name='schedule-create'),
    path('schedules/<int:pk>/update/', views.schedule_update, name='schedule-update'),
    path('my-schedules/', views.student_schedule_list, name='student-schedule-list'),
    path('patient-cases/', views.patient_case_list, name='patient-case-list'),
    path('patient-cases/create/', views.patient_case_create, name='patient-case-create'),
    path('my-cases/', views.my_cases, name='my-cases'),
    path('notifications/', views.notifications, name='notifications'),
]
