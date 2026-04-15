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


class ProtectedPageSecurityTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='secured-instructor',
            password='testpass123',
        )
        self.instructor.profile.role = Profile.ROLE_INSTRUCTOR
        self.instructor.profile.save()

        self.student = User.objects.create_user(
            username='secured-student',
            password='testpass123',
        )
        self.student.profile.role = Profile.ROLE_STUDENT
        self.student.profile.created_by = self.instructor
        self.student.profile.save()

    def assertNeverCache(self, response):
        self.assertIn('no-cache', response.headers['Cache-Control'])
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertIn('must-revalidate', response.headers['Cache-Control'])
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertIn('Expires', response.headers)

    def test_dashboard_redirects_unauthenticated_users_to_login(self):
        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("dashboard")}',
        )

    def test_dashboard_response_is_not_cacheable(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertNeverCache(response)

    def test_role_protected_response_is_not_cacheable(self):
        self.client.force_login(self.instructor)

        response = self.client.get(reverse('schedule-list'))

        self.assertEqual(response.status_code, 200)
        self.assertNeverCache(response)


class GroupRosterViewTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='roster-instructor',
            password='testpass123',
            first_name='Rae',
            last_name='Instructor',
        )
        self.instructor.profile.role = Profile.ROLE_INSTRUCTOR
        self.instructor.profile.save()

        self.other_instructor = User.objects.create_user(
            username='other-instructor',
            password='testpass123',
        )
        self.other_instructor.profile.role = Profile.ROLE_INSTRUCTOR
        self.other_instructor.profile.save()

        self.student = User.objects.create_user(
            username='student-roster',
            password='testpass123',
            first_name='Aly',
            last_name='Student',
        )
        self.student.profile.role = Profile.ROLE_STUDENT
        self.student.profile.student_id = 'C-2026-007'
        self.student.profile.year_level = '3'
        self.student.profile.section = 'A'
        self.student.profile.created_by = self.instructor
        self.student.profile.save()

        self.group = DutyGroup.objects.create(
            name='Ward A',
            instructor=self.instructor,
        )
        DutyGroupMembership.objects.create(
            duty_group=self.group,
            student=self.student,
        )

    def test_instructor_group_list_shows_view_students_button(self):
        self.client.force_login(self.instructor)

        response = self.client.get(reverse('group-list'))

        self.assertContains(response, 'View Students')
        self.assertContains(response, reverse('group-students', args=[self.group.pk]))

    def test_group_students_page_shows_enrolled_students(self):
        self.client.force_login(self.instructor)

        response = self.client.get(reverse('group-students', args=[self.group.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ward A')
        self.assertContains(response, 'Aly Student')
        self.assertContains(response, 'C-2026-007')
        self.assertContains(response, '3 / A')
        self.assertContains(response, 'Code:')
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_instructor_cannot_view_another_instructors_roster(self):
        other_group = DutyGroup.objects.create(
            name='Ward B',
            instructor=self.other_instructor,
        )

        self.client.force_login(self.instructor)

        response = self.client.get(reverse('group-students', args=[other_group.pk]))

        self.assertEqual(response.status_code, 404)
