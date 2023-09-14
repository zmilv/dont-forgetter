import pytest
from celery.contrib.testing.worker import start_worker
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import SimpleTestCase
from freezegun import freeze_time

import core.tasks
from backend.celery import app
from core.models import Event
from core.tasks import (
    EmailNotification,
    NotificationEvent,
    NotificationService,
    NotificationStrategy,
    SMSNotification,
    heartbeat,
    reset_notifications_left,
)
from users.models import CustomUser


@pytest.mark.django_db
class TestNotificationStrategy:
    @pytest.fixture()
    def strategy(self):
        mock_user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )
        mock_event = Event.objects.create(
            title=f"Title",
            date=f"2024-01-01",
            notification_type="email",
            user=mock_user,
        )

        class MockNotificationStrategy(NotificationStrategy):
            def send_notification(self):
                pass

        return MockNotificationStrategy(mock_event)

    def test_get_message_without_custom_message(self, strategy, mocker):
        strategy.event.custom_message = None
        mock_build_default_message = mocker.patch(
            "core.tasks.NotificationStrategy.build_default_message",
            return_value="default_message",
        )
        result = strategy.get_message()
        assert result == "default_message"
        mock_build_default_message.assert_called_once_with()

    def test_get_message_with_custom_message_and_custom_variables(
        self, strategy, mocker
    ):
        strategy.event.custom_message = "custom_message"
        strategy.event.custom_variables = "custom_variables"
        strategy.variable_dict = "variable_dict"
        mock_build_custom_text = mocker.patch(
            "core.tasks.NotificationStrategy.build_custom_text",
            return_value="custom_text",
        )
        result = strategy.get_message()
        assert result == "custom_text"
        mock_build_custom_text.assert_called_once_with(
            "custom_message", "variable_dict"
        )

    def test_get_message_with_custom_message_without_custom_variables(self, strategy):
        strategy.event.custom_message = "custom_message"
        result = strategy.get_message()
        assert result == "custom_message"

    def test_build_custom_text(self, strategy):
        template = "hi {{name}}, your last name is {{surname}}"
        variable_dict = {"name": "Tom", "surname": "Smith"}
        result = strategy.build_custom_text(template, variable_dict)
        expected_result = "hi Tom, your last name is Smith"
        assert result == expected_result

    def test_build_custom_text_without_variables(self, strategy):
        template = "hello"
        variable_dict = {"name": "Tom", "surname": "Smith"}
        result = strategy.build_custom_text(template, variable_dict)
        expected_result = "hello"
        assert result == expected_result

    def test_parse_custom_message_variables_with_two_variables(self, strategy):
        strategy.event.custom_variables = "name=Tom; surname=Smith"
        result = strategy.parse_custom_message_variables()
        expected_result = {"name": "Tom", "surname": "Smith"}
        assert result == expected_result

    def test_parse_custom_message_variables_with_one_variable(self, strategy):
        strategy.event.custom_variables = "name=Tom"
        result = strategy.parse_custom_message_variables()
        expected_result = {"name": "Tom"}
        assert result == expected_result


@pytest.mark.django_db
class TestEmailNotification:
    @pytest.fixture()
    def email_notification(self):
        mock_user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )
        mock_event = Event.objects.create(
            title=f"Title",
            date=f"2024-01-01",
            notification_type="email",
            user=mock_user,
        )
        return EmailNotification(mock_event)

    def test_send_notification_success(self, email_notification, mocker):
        email_notification.email_title = "email_title"
        email_notification.message = "message"
        email_notification.event.recipient = "recipient"
        mock_send_email = mocker.patch("core.tasks.send_mail", return_value=1)
        result = email_notification.send_notification()
        expected_result = True
        assert result == expected_result
        mock_send_email.assert_called_once_with(
            "email_title", "message", None, ["recipient"], fail_silently=False
        )

    def test_send_notification_failed(self, email_notification, mocker):
        email_notification.email_title = "email_title"
        email_notification.message = "message"
        email_notification.event.recipient = "recipient"
        mock_send_email = mocker.patch("core.tasks.send_mail", return_value=0)
        result = email_notification.send_notification()
        expected_result = False
        assert result == expected_result
        mock_send_email.assert_called_once_with(
            "email_title", "message", None, ["recipient"], fail_silently=False
        )

    def test_get_email_title_without_custom_email_subject(
        self, email_notification, mocker
    ):
        email_notification.event.custom_email_subject = None
        mock_build_default_title = mocker.patch(
            "core.tasks.EmailNotification.build_default_title",
            return_value="default_title",
        )
        result = email_notification.get_email_title()
        assert result == "default_title"
        mock_build_default_title.assert_called_once_with()

    def test_get_email_title_with_custom_email_subject_and_custom_variables(
        self, email_notification, mocker
    ):
        email_notification.event.custom_email_subject = "custom_email_subject"
        email_notification.event.custom_variables = "custom_variables"
        email_notification.variable_dict = "variable_dict"
        mock_build_custom_text = mocker.patch(
            "core.tasks.NotificationStrategy.build_custom_text",
            return_value="custom_text",
        )
        result = email_notification.get_email_title()
        assert result == "custom_text"
        mock_build_custom_text.assert_called_once_with(
            "custom_email_subject", "variable_dict"
        )

    def test_get_email_title_with_custom_email_subject_without_custom_variables(
        self, email_notification
    ):
        email_notification.event.custom_email_subject = "custom_email_subject"
        result = email_notification.get_email_title()
        assert result == "custom_email_subject"


@pytest.mark.django_db
class TestSMSNotification:
    @pytest.fixture()
    def sms_notification(self):
        mock_user = CustomUser.objects.create_user(
            email="email@email.com",
            username="name",
            password=make_password("password"),
        )
        mock_event = Event.objects.create(
            title=f"Title",
            date=f"2024-01-01",
            notification_type="sms",
            user=mock_user,
            recipient="37069935951",
        )
        return SMSNotification(mock_event)

    def test_send_sms_success(self, sms_notification, mocker):
        sms_notification.event.user.usersettings.sms_sender_name = "sender_name"
        sms_notification.event.recipient = "recipient"
        sms_notification.message = "message"

        mocker.patch.object(core.tasks, "vonage_api_key", "key")
        mocker.patch.object(core.tasks, "vonage_api_secret", "secret")
        url = "https://rest.nexmo.com/sms/json"
        params = {
            "api_key": "key",
            "api_secret": "secret",
            "from": "sender_name",
            "to": "recipient",
            "text": "message",
        }

        class MockResponse:
            @staticmethod
            def json():
                return {"messages": [{"status": "0"}]}

        mock_post = mocker.patch(
            "core.tasks.requests.Session.post", return_value=MockResponse
        )

        result = sms_notification.send_notification()
        expected_result = True
        mock_post.assert_called_once_with(url, data=params)
        assert result == expected_result

    def test_send_sms_failed(self, sms_notification, mocker):
        sms_notification.event.user.usersettings.sms_sender_name = "sender_name"
        sms_notification.event.recipient = "recipient"
        sms_notification.message = "message"

        mocker.patch.object(core.tasks, "vonage_api_key", "key")
        mocker.patch.object(core.tasks, "vonage_api_secret", "secret")
        url = "https://rest.nexmo.com/sms/json"
        params = {
            "api_key": "key",
            "api_secret": "secret",
            "from": "sender_name",
            "to": "recipient",
            "text": "message",
        }

        class MockResponse:
            @staticmethod
            def json():
                return {"messages": [{"status": "1"}]}

        mock_post = mocker.patch(
            "core.tasks.requests.Session.post", return_value=MockResponse
        )

        result = sms_notification.send_notification()
        expected_result = False
        mock_post.assert_called_once_with(url, data=params)
        assert result == expected_result


@pytest.mark.django_db
class TestNotificationService:
    @pytest.fixture()
    def service(self):
        mock_user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )
        mock_event = Event.objects.create(
            title=f"Title",
            date=f"2024-01-01",
            notification_type="email",
            user=mock_user,
        )
        return NotificationService(mock_event)

    def test_send_notification_no_interval(self, service, mocker):
        service.strategy = EmailNotification
        service.event.interval = "-"
        service.event.user.premium_member = False
        mock_send_notification = mocker.patch(
            "core.tasks.EmailNotification.send_notification", return_value=True
        )
        mock_decrement_notifications_left = mocker.patch(
            "core.tasks.NotificationService.decrement_notifications_left",
            return_value=True,
        )
        result = service.send_notification()
        expected_result = True
        assert result == expected_result
        mock_send_notification.assert_called_once_with()
        mock_decrement_notifications_left.assert_called_once_with()

    def test_send_notification_with_count(self, service, mocker):
        service.strategy = EmailNotification
        service.event.interval = "30min"
        service.event.count = 2
        service.event.user.premium_member = False
        mock_send_notification = mocker.patch(
            "core.tasks.EmailNotification.send_notification", return_value=True
        )
        mock_decrement_notifications_left = mocker.patch(
            "core.tasks.NotificationService.decrement_notifications_left",
            return_value=True,
        )
        result = service.send_notification()
        expected_result = True
        assert result == expected_result
        mock_send_notification.assert_called_once_with()
        mock_decrement_notifications_left.assert_called_once_with()
        assert service.event.count == 1

    def test_send_notification_premium_member(self, service, mocker):
        service.strategy = EmailNotification
        service.event.interval = "-"
        service.event.user.premium_member = True
        mock_send_notification = mocker.patch(
            "core.tasks.EmailNotification.send_notification", return_value=True
        )
        mock_decrement_notifications_left = mocker.patch(
            "core.tasks.NotificationService.decrement_notifications_left",
            return_value=True,
        )
        result = service.send_notification()
        expected_result = True
        assert result == expected_result
        mock_send_notification.assert_called_once_with()
        mock_decrement_notifications_left.assert_not_called()

    def test_send_notification_failed(self, service, mocker):
        service.strategy = EmailNotification
        service.event.notification_retries_left = 1
        mock_send_notification = mocker.patch(
            "core.tasks.EmailNotification.send_notification", return_value=False
        )
        mock_decrement_notifications_left = mocker.patch(
            "core.tasks.NotificationService.decrement_notifications_left",
            return_value=True,
        )
        result = service.send_notification()
        expected_result = False
        assert result == expected_result
        mock_send_notification.assert_called_once_with()
        mock_decrement_notifications_left.assert_not_called()
        assert service.event.notification_retries_left == 0

    def test_send_notification_failed_no_retries_left(self, service, mocker):
        service.strategy = EmailNotification
        service.event.notification_retries_left = 0
        mock_send_notification = mocker.patch(
            "core.tasks.EmailNotification.send_notification", return_value=False
        )
        mock_decrement_notifications_left = mocker.patch(
            "core.tasks.NotificationService.decrement_notifications_left",
            return_value=True,
        )
        result = service.send_notification()
        expected_result = True
        assert result == expected_result
        mock_send_notification.assert_called_once_with()
        mock_decrement_notifications_left.assert_not_called()
        assert service.event.notification_retries_left == 0

    def test_decrement_notifications_left(self, service, mocker):
        service.event.user.email_notifications_left = 2
        mock_send_notification_limit_email = mocker.patch(
            "core.tasks.NotificationService.send_notification_limit_email"
        )
        result = service.decrement_notifications_left()
        assert result == True
        assert service.event.user.email_notifications_left == 1
        mock_send_notification_limit_email.assert_not_called()

    def test_decrement_notifications_left_last_notification(self, service, mocker):
        service.event.user.email_notifications_left = 1
        mock_send_notification_limit_email = mocker.patch(
            "core.tasks.NotificationService.send_notification_limit_email"
        )
        result = service.decrement_notifications_left()
        expected_result = False
        assert result == expected_result
        assert service.event.user.email_notifications_left == 0
        mock_send_notification_limit_email.assert_called_with()


@pytest.mark.django_db
class TestNotificationEvent:
    @pytest.fixture()
    def notification_event(self):
        mock_user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )
        mock_event = Event.objects.create(
            title=f"Title",
            date=f"2020-01-01",
            time="10:00",
            notification_type="email",
            user=mock_user,
        )
        return NotificationEvent(mock_event, 1577873100)

    def test_reschedule_or_delete_event_deleted_no_interval(self, notification_event):
        notification_event.event.interval = "-"
        assert Event.objects.count() == 1
        notification_event.reschedule_or_delete_event()
        assert Event.objects.count() == 0

    def test_reschedule_or_delete_event_deleted_count_0(self, notification_event):
        notification_event.event.interval = "30min"
        notification_event.event.count = 0
        assert Event.objects.count() == 1
        notification_event.reschedule_or_delete_event()
        assert Event.objects.count() == 0

    def test_reschedule_or_delete_event_rescheduled(self, notification_event, mocker):
        notification_event.event.interval = "30min"
        notification_event.event.count = 1
        mock_send_notification_limit_email = mocker.patch(
            "core.tasks.NotificationEvent.reschedule_event"
        )
        assert Event.objects.count() == 1
        notification_event.reschedule_or_delete_event()
        assert Event.objects.count() == 1
        mock_send_notification_limit_email.assert_called_once_with()

    def test_get_new_date_and_time(self, notification_event):
        notification_event.current_utc_timestamp = 1577873100
        notification_event.event.date = "2020-01-01"
        notification_event.event.time = "10:00"
        notification_event.event.interval = "30min"
        notification_event.event.utc_offset = "+0"
        result = notification_event.get_new_date_and_time()
        expected_result = ("2020-01-01", "10:30")
        assert result == expected_result


@freeze_time("2020-01-01 10:05")  # Mocks current datetime
class TestCeleryIntegration(SimpleTestCase):
    databases = "__all__"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )
        # Start celery worker
        cls.celery_worker = start_worker(app, perform_ping_check=False)
        cls.celery_worker.__enter__()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Close worker
        cls.celery_worker.__exit__(None, None, None)

    def _post_teardown(self):
        # Clear Event instances after each test
        Event.objects.all().delete()

    def test_heartbeat_without_interval(self):
        Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            notification_type="email",
            user=self.user,
        )
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should be deleted
        heartbeat_task.get()
        result = heartbeat_task.get()
        notification_and_reschedule_task = AsyncResult(id=result[0], app=app)
        notification_and_reschedule_task.get()
        self.assertEqual(heartbeat_task.status, "SUCCESS")
        self.assertEqual(notification_and_reschedule_task.status, "SUCCESS")
        self.assertEqual(Event.objects.count(), 0)

    def test_heartbeat_with_interval(self):
        Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            interval="30min",
            utc_offset="+0",
            notification_type="email",
            user=self.user,
        )
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should be updated
        heartbeat_task.get()
        result = heartbeat_task.get()
        notification_and_reschedule_task = AsyncResult(id=result[0], app=app)
        notification_and_reschedule_task.get()
        self.assertEqual(heartbeat_task.status, "SUCCESS")
        self.assertEqual(notification_and_reschedule_task.status, "SUCCESS")
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_heartbeat_with_missed_timestamp(self):
        Event.objects.create(
            title=f"Title-1",
            date="2019-01-01",
            time="10:00",
            interval="30min",
            utc_offset="+0",
            notification_type="email",
            user=self.user,
        )
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should be updated
        heartbeat_task.get()
        result = heartbeat_task.get()
        notification_and_reschedule_task = AsyncResult(id=result[0], app=app)
        notification_and_reschedule_task.get()
        self.assertEqual(heartbeat_task.status, "SUCCESS")
        self.assertEqual(notification_and_reschedule_task.status, "SUCCESS")
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_heartbeat_without_expired_events(self):
        Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="11:00",
            utc_offset="+0",
            notification_type="email",
            user=self.user,
        )
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should remain unchanged
        result = heartbeat_task.get()
        self.assertEqual(result, [])
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "11:00")

    def test_reset_notifications_left(self):
        CustomUser.objects.create_user(
            email="reset@email.com",
            username="reset",
            password=make_password("password"),
            email_notifications_left=0,
            sms_notifications_left=0,
        )
        self.assertEqual(
            CustomUser.objects.get(username="reset").email_notifications_left, 0
        )
        self.assertEqual(
            CustomUser.objects.get(username="reset").sms_notifications_left, 0
        )
        task = reset_notifications_left.delay()
        task.get()
        self.assertEqual(task.status, "SUCCESS")
        self.assertEqual(
            CustomUser.objects.get(username="reset").email_notifications_left,
            settings.NO_OF_FREE_EMAIL_NOTIFICATIONS,
        )
        self.assertEqual(
            CustomUser.objects.get(username="reset").sms_notifications_left,
            settings.NO_OF_FREE_SMS_NOTIFICATIONS,
        )
