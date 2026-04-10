from django.conf import settings
from django.db import models


class Profile(models.Model):
    ROLE_ADMIN = 'ADMIN'
    ROLE_INSTRUCTOR = 'INSTRUCTOR'
    ROLE_STUDENT = 'STUDENT'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_INSTRUCTOR, 'Clinical Instructor'),
        (ROLE_STUDENT, 'Student'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    student_id = models.CharField(max_length=30, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_student_profiles',
    )
    year_level = models.CharField(max_length=20, blank=True)
    section = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.role}"
