from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import AccountLoginForm


class AccountLoginViewTests(TestCase):
    def setUp(self):
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username='C-2023-001',
            password=self.password,
        )

    def test_login_page_renders_password_toggle_controls(self):
        response = self.client.get(reverse('login'))

        self.assertContains(response, 'portal-role-logo-v3.png')
        self.assertContains(response, 'data-password-toggle')
        self.assertContains(response, 'data-target="id_password"')
        self.assertContains(response, 'Show')

    def test_login_page_disables_username_suggestions(self):
        response = self.client.get(reverse('login'))

        self.assertContains(response, 'id="id_username"')
        self.assertContains(response, 'autocomplete="off"')
        self.assertContains(response, 'autocapitalize="none"')
        self.assertContains(response, 'autocorrect="off"')
        self.assertContains(response, 'spellcheck="false"')
        self.assertContains(response, 'readonly')
        self.assertContains(response, 'data-plain-text-input')
        self.assertContains(response, 'data-lpignore="true"')
        self.assertContains(response, 'data-1p-ignore="true"')
        self.assertNotContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="current-password"')

    def test_login_page_is_not_cacheable(self):
        response = self.client.get(reverse('login'))

        self.assertIn('no-cache', response.headers['Cache-Control'])
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertIn('must-revalidate', response.headers['Cache-Control'])
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertIn('Expires', response.headers)

    def test_authenticated_user_is_redirected_away_from_login_page(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('login'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_invalid_login_shows_generic_error_message(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': self.user.username,
                'password': 'wrong-password',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, AccountLoginForm.INVALID_CREDENTIALS_MESSAGE)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_locks_after_max_failed_attempts(self):
        with patch('accounts.forms.time.time', return_value=1000):
            for _ in range(AccountLoginForm.MAX_FAILED_ATTEMPTS - 1):
                response = self.client.post(
                    reverse('login'),
                    {
                        'username': self.user.username,
                        'password': 'wrong-password',
                    },
                )
                self.assertContains(response, AccountLoginForm.INVALID_CREDENTIALS_MESSAGE)

            response = self.client.post(
                reverse('login'),
                {
                    'username': self.user.username,
                    'password': 'wrong-password',
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, AccountLoginForm.LOCKOUT_MESSAGE)
        self.assertTrue(response.context['form'].lockout_active)
        self.assertEqual(
            response.context['form'].lockout_seconds_remaining,
            AccountLoginForm.LOCKOUT_SECONDS,
        )

        with patch('accounts.forms.time.time', return_value=1010):
            locked_response = self.client.post(
                reverse('login'),
                {
                    'username': self.user.username,
                    'password': self.password,
                },
            )

        self.assertEqual(locked_response.status_code, 200)
        self.assertContains(locked_response, AccountLoginForm.LOCKOUT_MESSAGE)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_succeeds_after_lockout_expires(self):
        with patch('accounts.forms.time.time', return_value=1000):
            for _ in range(AccountLoginForm.MAX_FAILED_ATTEMPTS):
                self.client.post(
                    reverse('login'),
                    {
                        'username': self.user.username,
                        'password': 'wrong-password',
                    },
                )

        with patch('accounts.forms.time.time', return_value=1031):
            response = self.client.post(
                reverse('login'),
                {
                    'username': self.user.username,
                    'password': self.password,
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))
        self.assertEqual(str(self.client.session['_auth_user_id']), str(self.user.pk))

    def test_logout_redirects_to_login_and_blocks_dashboard_access(self):
        self.client.force_login(self.user)

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)

        logout_response = self.client.post(reverse('logout'))

        self.assertRedirects(logout_response, reverse('login'))
        self.assertIn('no-cache', logout_response.headers['Cache-Control'])
        self.assertIn('no-store', logout_response.headers['Cache-Control'])

        redirected_response = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            redirected_response,
            f'{reverse("login")}?next={reverse("dashboard")}',
        )
