from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

from .models import ClinicalArea, DutyGroup, DutyGroupMembership, DutySchedule


class ScheduleCreateTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor1',
            password='testpass123',
        )
        self.instructor.profile.role = Profile.ROLE_INSTRUCTOR
        self.instructor.profile.save()

        self.student = User.objects.create_user(
            username='student1',
            password='testpass123',
        )
        self.student.profile.role = Profile.ROLE_STUDENT
        self.student.profile.created_by = self.instructor
        self.student.profile.save()

        self.group = DutyGroup.objects.create(
            name='Section A',
            instructor=self.instructor,
        )
        DutyGroupMembership.objects.create(
            duty_group=self.group,
            student=self.student,
        )

    def test_schedule_create_accepts_new_clinical_area_name(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse('schedule-create'),
            {
                'title': 'Morning Duty',
                'clinical_area_name': 'ER',
                'student': self.student.pk,
                'duty_date': '2026-04-10',
                'start_time': '08:00',
                'end_time': '12:00',
                'status': DutySchedule.STATUS_PENDING,
                'notes': 'Observe triage workflow.',
            },
        )

        self.assertRedirects(response, reverse('schedule-list'))
        self.assertEqual(DutySchedule.objects.count(), 1)
        self.assertEqual(ClinicalArea.objects.count(), 1)
        self.assertEqual(DutySchedule.objects.get().clinical_area.name, 'ER')

    def test_schedule_create_reuses_existing_clinical_area_case_insensitively(self):
        existing_area = ClinicalArea.objects.create(name='ER')
        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse('schedule-create'),
            {
                'title': 'Evening Duty',
                'clinical_area_name': 'er',
                'student': self.student.pk,
                'duty_date': '2026-04-11',
                'start_time': '13:00',
                'end_time': '17:00',
                'status': DutySchedule.STATUS_PENDING,
                'notes': '',
            },
        )

        self.assertRedirects(response, reverse('schedule-list'))
        self.assertEqual(ClinicalArea.objects.count(), 1)
        self.assertEqual(DutySchedule.objects.get().clinical_area_id, existing_area.id)
