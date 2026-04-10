from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('password/change/', views.AccountPasswordChangeView.as_view(), name='password-change'),
    path('students/', views.student_list, name='student-list'),
    path('students/create/', views.student_create, name='student-create'),
    path('students/<int:pk>/edit/', views.student_update, name='student-update'),
]
