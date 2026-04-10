import random
import string
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class ClinicalArea(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class DutySchedule(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    title = models.CharField(max_length=150)
    clinical_area = models.ForeignKey(ClinicalArea, on_delete=models.CASCADE)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructor_schedules')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_schedules')
    duty_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['duty_date', 'start_time']

    def clean(self):
        overlapping = DutySchedule.objects.filter(
            student=self.student,
            duty_date=self.duty_date,
        ).exclude(pk=self.pk)
        for schedule in overlapping:
            if self.start_time < schedule.end_time and self.end_time > schedule.start_time:
                raise ValidationError('Student already has an overlapping duty schedule.')

    def __str__(self):
        return f"{self.student.username} - {self.clinical_area.name} - {self.duty_date}"


class PatientCase(models.Model):
    CASE_LOW = 'LOW'
    CASE_MODERATE = 'MODERATE'
    CASE_HIGH = 'HIGH'
    ACUITY_CHOICES = [
        (CASE_LOW, 'Low'),
        (CASE_MODERATE, 'Moderate'),
        (CASE_HIGH, 'High'),
    ]

    duty_schedule = models.ForeignKey(DutySchedule, on_delete=models.CASCADE, related_name='patient_cases')
    case_title = models.CharField(max_length=150)
    patient_code = models.CharField(max_length=50)
    diagnosis = models.CharField(max_length=150)
    acuity_level = models.CharField(max_length=20, choices=ACUITY_CHOICES)
    remarks = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.case_title} - {self.patient_code}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class DutyHistory(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duty_histories')
    duty_schedule = models.ForeignKey(DutySchedule, on_delete=models.CASCADE)
    patient_case = models.ForeignKey(PatientCase, on_delete=models.SET_NULL, null=True, blank=True)
    exposure_type = models.CharField(max_length=150)
    completed_on = models.DateField()

    class Meta:
        ordering = ['-completed_on']

    def __str__(self):
        return f"{self.student.username} - {self.exposure_type}"


def generate_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(alphabet, k=6))
        if not DutyGroup.objects.filter(join_code=code).exists():
            return code


class DutyGroup(models.Model):
    name = models.CharField(max_length=100)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duty_groups')
    join_code = models.CharField(max_length=10, unique=True, default=generate_code, editable=False)
    students = models.ManyToManyField(
        User,
        through='DutyGroupMembership',
        related_name='joined_duty_groups',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['instructor', 'name'], name='unique_duty_group_name_per_instructor'),
        ]

    def __str__(self):
        return f"{self.name} ({self.join_code})"


class DutyGroupMembership(models.Model):
    duty_group = models.ForeignKey(DutyGroup, on_delete=models.CASCADE, related_name='memberships')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duty_group_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-joined_at']
        constraints = [
            models.UniqueConstraint(fields=['duty_group', 'student'], name='unique_duty_group_membership'),
        ]

    def __str__(self):
        return f"{self.student.username} in {self.duty_group.name}"
