from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from notifications.models import Notification
from notifications.utils import notify

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username, password='pass1234', role='citizen', is_active=True):
    return User.objects.create_user(
        username=username, password=password, role=role, is_active=is_active
    )


def make_notification(user, title='Test Title', message='Test message',
                      notif_type='general', is_read=False):
    return Notification.objects.create(
        user=user, title=title, message=message,
        notif_type=notif_type, is_read=is_read,
    )


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class NotificationModelTest(TestCase):

    def setUp(self):
        self.user = make_user('notifuser')
        self.notif = make_notification(self.user, title='Welcome', message='Hello!')

    def test_str_representation(self):
        self.assertEqual(str(self.notif), f"Notification for {self.user.username}")

    def test_default_is_read_is_false(self):
        self.assertFalse(self.notif.is_read)

    def test_default_notif_type_is_general(self):
        self.assertEqual(self.notif.notif_type, 'general')

    def test_created_at_is_set_automatically(self):
        self.assertIsNotNone(self.notif.created_at)

    def test_ordering_latest_first(self):
        older = make_notification(self.user, title='Older')
        newer = make_notification(self.user, title='Newer')
        notifs = list(Notification.objects.filter(user=self.user))
        self.assertEqual(notifs[0], newer)
        self.assertEqual(notifs[-1], self.notif)

    def test_notification_belongs_to_correct_user(self):
        self.assertEqual(self.notif.user, self.user)

    def test_issue_is_optional(self):
        self.assertIsNone(self.notif.issue)

    def test_all_notif_types_are_valid(self):
        valid_types = [
            'issue_submitted', 'status_changed', 'issue_assigned',
            'issue_resolved', 'issue_rejected', 'remark_added', 'general'
        ]
        for notif_type in valid_types:
            n = make_notification(self.user, notif_type=notif_type)
            self.assertEqual(n.notif_type, notif_type)

    def test_mark_as_read(self):
        self.notif.is_read = True
        self.notif.save()
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_multiple_notifications_for_same_user(self):
        make_notification(self.user, title='Second')
        make_notification(self.user, title='Third')
        count = Notification.objects.filter(user=self.user).count()
        self.assertEqual(count, 3)

    def test_deleting_user_deletes_notifications(self):
        user2 = make_user('deleteuser')
        make_notification(user2, title='To be deleted')
        user2.delete()
        self.assertEqual(Notification.objects.filter(user__username='deleteuser').count(), 0)


# ---------------------------------------------------------------------------
# Utils Tests
# ---------------------------------------------------------------------------

class NotifyUtilTest(TestCase):

    def setUp(self):
        self.user = make_user('utiluser')

    def test_notify_creates_notification(self):
        notify(self.user, title='Hello', message='Test message')
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_notify_sets_correct_title(self):
        notify(self.user, title='Issue Submitted', message='Your issue was submitted.')
        notif = Notification.objects.get(user=self.user)
        self.assertEqual(notif.title, 'Issue Submitted')

    def test_notify_sets_correct_message(self):
        notify(self.user, title='Hi', message='Your issue was resolved.')
        notif = Notification.objects.get(user=self.user)
        self.assertEqual(notif.message, 'Your issue was resolved.')

    def test_notify_default_type_is_general(self):
        notify(self.user, title='Hi', message='Hello')
        notif = Notification.objects.get(user=self.user)
        self.assertEqual(notif.notif_type, 'general')

    def test_notify_custom_type(self):
        notify(self.user, title='Resolved', message='Done', notif_type='issue_resolved')
        notif = Notification.objects.get(user=self.user)
        self.assertEqual(notif.notif_type, 'issue_resolved')

    def test_notify_is_unread_by_default(self):
        notify(self.user, title='New', message='Unread notif')
        notif = Notification.objects.get(user=self.user)
        self.assertFalse(notif.is_read)

    def test_notify_issue_defaults_to_none(self):
        notify(self.user, title='General', message='No issue linked')
        notif = Notification.objects.get(user=self.user)
        self.assertIsNone(notif.issue)

    def test_notify_multiple_calls_create_multiple_notifications(self):
        notify(self.user, title='First', message='msg1')
        notify(self.user, title='Second', message='msg2')
        notify(self.user, title='Third', message='msg3')
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 3)


# ---------------------------------------------------------------------------
# View Tests: notifications list
# ---------------------------------------------------------------------------

class NotificationsViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user('viewuser')
        self.url = reverse('notifications')

    def test_redirects_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_logged_in_user_can_access(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'citizen/notifications.html')

    def test_notifications_shown_in_context(self):
        self.client.force_login(self.user)
        make_notification(self.user, title='Notif 1')
        make_notification(self.user, title='Notif 2')
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['notifications']), 2)

    def test_visiting_page_marks_all_as_read(self):
        self.client.force_login(self.user)
        make_notification(self.user, is_read=False)
        make_notification(self.user, is_read=False)
        self.client.get(self.url)
        unread = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread, 0)

    def test_user_only_sees_own_notifications(self):
        other_user = make_user('otheruser')
        self.client.force_login(self.user)
        make_notification(self.user, title='Mine')
        make_notification(other_user, title='Not mine')
        response = self.client.get(self.url)
        for notif in response.context['notifications']:
            self.assertEqual(notif.user, self.user)

    def test_empty_notifications_returns_empty_list(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['notifications']), 0)


# ---------------------------------------------------------------------------
# View Tests: mark_notification_read
# ---------------------------------------------------------------------------

class MarkNotificationReadViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user('markuser')
        self.notif = make_notification(self.user, is_read=False)
        self.url = reverse('mark_notification_read', args=[self.notif.pk])

    def test_redirects_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_marks_notification_as_read(self):
        self.client.force_login(self.user)
        self.client.get(self.url)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_redirects_to_notifications_when_no_issue(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('notifications'))

    def test_cannot_mark_another_users_notification(self):
        other_user = make_user('othermark')
        self.client.force_login(other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_invalid_pk_returns_404(self):
        self.client.force_login(self.user)
        url = reverse('mark_notification_read', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# View Tests: mark_all_read
# ---------------------------------------------------------------------------

class MarkAllReadViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user('allreaduser')
        self.url = reverse('mark_all_read')

    def test_redirects_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_marks_all_unread_notifications_as_read(self):
        self.client.force_login(self.user)
        make_notification(self.user, is_read=False)
        make_notification(self.user, is_read=False)
        make_notification(self.user, is_read=False)
        self.client.get(self.url)
        unread = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread, 0)

    def test_does_not_affect_other_users_notifications(self):
        other_user = make_user('otheralread')
        self.client.force_login(self.user)
        make_notification(other_user, is_read=False)
        self.client.get(self.url)
        other_unread = Notification.objects.filter(user=other_user, is_read=False).count()
        self.assertEqual(other_unread, 1)

    def test_already_read_notifications_stay_read(self):
        self.client.force_login(self.user)
        make_notification(self.user, is_read=True)
        self.client.get(self.url)
        read_count = Notification.objects.filter(user=self.user, is_read=True).count()
        self.assertEqual(read_count, 1)

    def test_works_when_no_notifications_exist(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [200, 302])