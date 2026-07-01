from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from unittest.mock import patch, MagicMock

from accounts.models import User, UserActivityLog
from accounts.forms import CitizenRegistrationForm
from accounts.tokens import account_activation_token
from accounts.signals import get_device, get_ip


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class UserModelTest(TestCase):

    def setUp(self):
        self.citizen = User.objects.create_user(
            username='citizen1', password='pass1234', role='citizen'
        )
        self.officer = User.objects.create_user(
            username='officer1', password='pass1234', role='officer'
        )
        self.admin = User.objects.create_user(
            username='admin1', password='pass1234', role='admin'
        )

    def test_is_citizen_returns_true_for_citizen(self):
        self.assertTrue(self.citizen.is_citizen())

    def test_is_citizen_returns_false_for_others(self):
        self.assertFalse(self.officer.is_citizen())
        self.assertFalse(self.admin.is_citizen())

    def test_is_officer_returns_true_for_officer(self):
        self.assertTrue(self.officer.is_officer())

    def test_is_officer_returns_false_for_others(self):
        self.assertFalse(self.citizen.is_officer())
        self.assertFalse(self.admin.is_officer())

    def test_is_admin_returns_true_for_admin(self):
        self.assertTrue(self.admin.is_admin())

    def test_is_admin_returns_false_for_others(self):
        self.assertFalse(self.citizen.is_admin())
        self.assertFalse(self.officer.is_admin())

    def test_default_role_is_citizen(self):
        user = User.objects.create_user(username='newuser', password='pass1234')
        self.assertEqual(user.role, 'citizen')

    def test_default_ward_number(self):
        user = User.objects.create_user(username='warduser', password='pass1234')
        self.assertEqual(user.ward_number, 1)

    def test_phone_number_optional(self):
        user = User.objects.create_user(username='nophone', password='pass1234')
        self.assertIsNone(user.phone_number)


class UserActivityLogTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='loguser', password='pass1234')
        self.log = UserActivityLog.objects.create(
            user=self.user,
            login_time=timezone.now(),
            ip_address='127.0.0.1',
            device='Desktop · Chrome · Windows',
            session_key='abc123',
        )

    def test_str_representation(self):
        result = str(self.log)
        self.assertIn('loguser', result)
        self.assertIn('logged in', result)

    def test_duration_returns_active_when_no_logout(self):
        self.assertEqual(self.log.duration, 'Active')

    def test_duration_in_seconds(self):
        self.log.logout_time = self.log.login_time + timezone.timedelta(seconds=45)
        self.assertEqual(self.log.duration, '45s')

    def test_duration_in_minutes(self):
        self.log.logout_time = self.log.login_time + timezone.timedelta(minutes=5, seconds=30)
        self.assertEqual(self.log.duration, '5m 30s')

    def test_duration_in_hours(self):
        self.log.logout_time = self.log.login_time + timezone.timedelta(hours=2, minutes=15)
        self.assertEqual(self.log.duration, '2h 15m')

    def test_ordering_latest_first(self):
        older_log = UserActivityLog.objects.create(
            user=self.user,
            login_time=timezone.now() - timezone.timedelta(hours=2),
        )
        logs = list(UserActivityLog.objects.all())
        self.assertEqual(logs[0], self.log)


# ---------------------------------------------------------------------------
# Form Tests
# ---------------------------------------------------------------------------

class CitizenRegistrationFormTest(TestCase):

    def get_valid_data(self, **overrides):
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '9800000000',
            'password1': 'StrongPass@123',
            'password2': 'StrongPass@123',
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = CitizenRegistrationForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_mismatched_passwords_invalid(self):
        form = CitizenRegistrationForm(
            data=self.get_valid_data(password2='WrongPass@123')
        )
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_duplicate_username_invalid(self):
        User.objects.create_user(username='testuser', password='pass1234')
        form = CitizenRegistrationForm(data=self.get_valid_data())
        self.assertFalse(form.is_valid())

    def test_missing_email_invalid(self):
        form = CitizenRegistrationForm(data=self.get_valid_data(email=''))
        self.assertFalse(form.is_valid())

    def test_form_fields_present(self):
        form = CitizenRegistrationForm()
        for field in ['username', 'email', 'phone_number', 'password1', 'password2']:
            self.assertIn(field, form.fields)


# ---------------------------------------------------------------------------
# View Tests: Register
# ---------------------------------------------------------------------------

class RegisterViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('register')

    def test_get_register_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    @patch('accounts.views.activateEmail')
    def test_successful_registration_sends_email(self, mock_email):
        response = self.client.post(self.url, {
            'username': 'newcitizen',
            'email': 'citizen@example.com',
            'phone_number': '9800000000',
            'password1': 'StrongPass@123',
            'password2': 'StrongPass@123',
        })
        self.assertEqual(response.status_code, 200)
        mock_email.assert_called_once()

    @patch('accounts.views.activateEmail')
    def test_registered_user_is_inactive(self, mock_email):
        self.client.post(self.url, {
            'username': 'inactiveuser',
            'email': 'inactive@example.com',
            'phone_number': '9800000000',
            'password1': 'StrongPass@123',
            'password2': 'StrongPass@123',
        })
        user = User.objects.get(username='inactiveuser')
        self.assertFalse(user.is_active)

    @patch('accounts.views.activateEmail')
    def test_registered_user_role_is_citizen(self, mock_email):
        self.client.post(self.url, {
            'username': 'rolecitizen',
            'email': 'role@example.com',
            'phone_number': '9800000000',
            'password1': 'StrongPass@123',
            'password2': 'StrongPass@123',
        })
        user = User.objects.get(username='rolecitizen')
        self.assertEqual(user.role, 'citizen')

    def test_invalid_registration_shows_errors(self):
        response = self.client.post(self.url, {
            'username': '',
            'email': 'bad-email',
            'password1': 'pass',
            'password2': 'different',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_authenticated_citizen_redirected_from_register(self):
        user = User.objects.create_user(
            username='existing', password='pass1234', role='citizen', is_active=True
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('citizen_dashboard'))

    def test_authenticated_admin_redirected_from_register(self):
        user = User.objects.create_user(
            username='adminuser', password='pass1234', role='admin', is_active=True
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('admin_dashboard'))


# ---------------------------------------------------------------------------
# View Tests: Login
# ---------------------------------------------------------------------------

class LoginViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('login')
        self.user = User.objects.create_user(
            username='activeuser', password='pass1234', role='citizen', is_active=True
        )

    def test_get_login_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_citizen_login_redirects_to_citizen_dashboard(self):
        response = self.client.post(self.url, {
            'username': 'activeuser',
            'password': 'pass1234',
        })
        self.assertRedirects(response, reverse('citizen_dashboard'))

    def test_admin_login_redirects_to_admin_dashboard(self):
        admin = User.objects.create_user(
            username='adminlogin', password='pass1234', role='admin', is_active=True
        )
        response = self.client.post(self.url, {
            'username': 'adminlogin',
            'password': 'pass1234',
        })
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_officer_login_redirects_to_officer_dashboard(self):
        officer = User.objects.create_user(
            username='officerlogin', password='pass1234', role='officer', is_active=True
        )
        response = self.client.post(self.url, {
            'username': 'officerlogin',
            'password': 'pass1234',
        })
        self.assertRedirects(response, reverse('officer_dashboard'))

    def test_invalid_credentials_shows_error(self):
        response = self.client.post(self.url, {
            'username': 'activeuser',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Invalid' in str(m) for m in messages))

    def test_inactive_user_cannot_login(self):
        User.objects.create_user(
            username='inactivelogin', password='pass1234', role='citizen', is_active=False
        )
        response = self.client.post(self.url, {
            'username': 'inactivelogin',
            'password': 'pass1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertFalse(response.wsgi_request.user.is_authenticated)


# ---------------------------------------------------------------------------
# View Tests: Logout
# ---------------------------------------------------------------------------

class LogoutViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='logoutuser', password='pass1234', is_active=True
        )
        self.client.force_login(self.user)

    def test_logout_redirects_to_login(self):
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_user_is_logged_out_after_logout(self):
        self.client.get(reverse('logout'))
        response = self.client.get(reverse('login'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


# ---------------------------------------------------------------------------
# View Tests: Activate
# ---------------------------------------------------------------------------

class ActivateViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='activateuser', password='pass1234', is_active=False
        )

    def _get_activation_url(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        return reverse('activate', kwargs={'uidb64': uid, 'token': token})

    @patch('accounts.views.EmailAddress')
    def test_valid_token_activates_user(self, mock_email_address):
        mock_email_address.objects.filter.return_value.update.return_value = None
        url = self._get_activation_url(self.user)
        self.client.get(url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_invalid_token_redirects_to_register(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse('activate', kwargs={'uidb64': uid, 'token': 'invalid-token'})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('register'))

    def test_invalid_uid_redirects_to_register(self):
        url = reverse('activate', kwargs={'uidb64': 'invaliduid', 'token': 'sometoken'})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('register'))


# ---------------------------------------------------------------------------
# Signal / Helper Tests
# ---------------------------------------------------------------------------

class GetDeviceTest(TestCase):

    def _mock_request(self, ua):
        request = MagicMock()
        request.META = {'HTTP_USER_AGENT': ua}
        return request

    def test_desktop_chrome_windows(self):
        ua = 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit Chrome/120'
        result = get_device(self._mock_request(ua))
        self.assertIn('Desktop', result)
        self.assertIn('Chrome', result)
        self.assertIn('Windows', result)

    def test_mobile_android(self):
        ua = 'Mozilla/5.0 (Android; Mobile) Chrome/120'
        result = get_device(self._mock_request(ua))
        self.assertIn('Mobile', result)
        self.assertIn('Android', result)

    def test_ipad_tablet(self):
        ua = 'Mozilla/5.0 (iPad; CPU OS 16) Safari/604'
        result = get_device(self._mock_request(ua))
        self.assertIn('Tablet', result)

    def test_firefox_linux(self):
        ua = 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko Firefox/120.0'
        result = get_device(self._mock_request(ua))
        self.assertIn('Firefox', result)
        self.assertIn('Linux', result)

    def test_unknown_ua(self):
        result = get_device(self._mock_request(''))
        self.assertIn('Unknown', result)


class GetIPTest(TestCase):

    def _mock_request(self, remote_addr=None, forwarded_for=None):
        request = MagicMock()
        meta = {}
        if remote_addr:
            meta['REMOTE_ADDR'] = remote_addr
        if forwarded_for:
            meta['HTTP_X_FORWARDED_FOR'] = forwarded_for
        request.META = meta
        return request

    def test_returns_remote_addr(self):
        result = get_ip(self._mock_request(remote_addr='192.168.1.1'))
        self.assertEqual(result, '192.168.1.1')

    def test_prefers_x_forwarded_for(self):
        result = get_ip(self._mock_request(
            remote_addr='10.0.0.1',
            forwarded_for='203.0.113.5, 10.0.0.1'
        ))
        self.assertEqual(result, '203.0.113.5')


# ---------------------------------------------------------------------------
# Token Tests
# ---------------------------------------------------------------------------

class AccountActivationTokenTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='tokenuser', password='pass1234', is_active=False
        )

    def test_token_is_valid_for_inactive_user(self):
        token = account_activation_token.make_token(self.user)
        self.assertTrue(account_activation_token.check_token(self.user, token))

    def test_token_invalid_after_activation(self):
        token = account_activation_token.make_token(self.user)
        self.user.is_active = True
        self.user.save()
        self.assertFalse(account_activation_token.check_token(self.user, token))

    def test_wrong_token_is_invalid(self):
        self.assertFalse(account_activation_token.check_token(self.user, 'bad-token'))