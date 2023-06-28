from datetime import datetime, timezone

import pytest
from celery.contrib.testing.worker import start_worker
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import SimpleTestCase, TestCase
from freezegun import freeze_time

import core.tasks
from backend.celery import app
from core.models import Event
from core.tasks import (
    decrement_notifications_left,
    get_new_date_and_time,
    heartbeat,
    reschedule_or_delete_event,
    reset_notifications_left,
    send_email,
    send_notification,
    send_sms,
)
from users.models import CustomUser


@pytest.mark.django_db
class TestNotificationTasks:
    def test_send_email_success(self, mocker):
        args_dict = {"title": "a", "text": "b", "email": "c"}
        mocked_func = mocker.patch("core.tasks.send_mail", return_value=1)

        result = send_email(args_dict)

        mocked_func.assert_called_once_with(
            args_dict["title"],
            args_dict["text"],
            None,
            [args_dict["email"]],
            fail_silently=False,
        )
        assert result == True

    def test_send_email_failed(self, mocker):
        args_dict = {"title": "a", "text": "b", "email": "c"}
        mocked_func = mocker.patch("core.tasks.send_mail", return_value=0)

        result = send_email(args_dict)

        mocked_func.assert_called_once_with(
            args_dict["title"],
            args_dict["text"],
            None,
            [args_dict["email"]],
            fail_silently=False,
        )
        assert result == False

    def test_send_sms_success(self, mocker):
        mocker.patch.object(core.tasks, "vonage_api_key", "key")
        mocker.patch.object(core.tasks, "vonage_api_secret", "secret")
        args_dict = {"phone_number": "a", "text": "b"}
        url = "https://rest.nexmo.com/sms/json"
        params = {
            "api_key": "key",
            "api_secret": "secret",
            "from": "dont-forgetter",
            "to": args_dict["phone_number"],
            "text": args_dict["text"],
        }

        class MockResponse:
            @staticmethod
            def json():
                return {"messages": [{"status": "0"}]}

        mocked_func = mocker.patch(
            "core.tasks.requests.Session.post", return_value=MockResponse
        )

        result = send_sms(args_dict)

        mocked_func.assert_called_once()
        mocked_func.assert_called_once_with(url, data=params)
        assert result == True

    def test_send_sms_failed(self, mocker):
        mocker.patch.object(core.tasks, "vonage_api_key", "key")
        mocker.patch.object(core.tasks, "vonage_api_secret", "secret")
        args_dict = {"phone_number": "a", "text": "b"}
        url = "https://rest.nexmo.com/sms/json"
        params = {
            "api_key": "key",
            "api_secret": "secret",
            "from": "dont-forgetter",
            "to": args_dict["phone_number"],
            "text": args_dict["text"],
        }

        class MockResponse:
            @staticmethod
            def json():
                return {"messages": [{"status": "1"}]}

        mocked_func = mocker.patch(
            "core.tasks.requests.Session.post", return_value=MockResponse
        )

        result = send_sms(args_dict)

        mocked_func.assert_called_once()
        mocked_func.assert_called_once_with(url, data=params)
        assert result == False

    def test_send_notification_success(self, mocker):
        user = CustomUser.objects.create_user(
            email="user@email.com",
            username="user",
            password=make_password("password"),
            email_notifications_left=1,
        )
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            user=user,
            notification_type="email",
        )
        mocker.patch(
            "core.tasks.build_notification_title_and_text",
            return_value=("mock_title", "mock_text"),
        )
        args_dict = {
            "title": "mock_title",
            "text": "mock_text",
            "email": event.user.email,
            "phone_number": event.user.phone_number,
        }
        # mocked_send_email_func = mocker.patch("core.tasks.send_email", return_value=True)
        mocked_send_email_func = mocker.patch("core.tasks.send_mail", return_value=1)
        mocked_decrement_func = mocker.patch("core.tasks.decrement_notifications_left")

        result = send_notification(event)

        assert result == True
        mocked_send_email_func.assert_called_once()
        # mocked_send_email_func.assert_called_once_with(args_dict)
        mocked_decrement_func.assert_called_once_with(event)

    def test_send_notification_out_of_notifications(self, mocker):
        user = CustomUser.objects.create_user(
            email="user@email.com",
            username="user",
            password=make_password("password"),
            email_notifications_left=0,
        )
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            user=user,
            notification_type="email",
        )
        mocker.patch(
            "core.tasks.build_notification_title_and_text",
            return_value=("mock_title", "mock_text"),
        )
        mocked_send_email_func = mocker.patch("core.tasks.send_mail")

        result = send_notification(event)

        assert result == True
        mocked_send_email_func.assert_not_called()

    def test_send_notification_failed(self, mocker):
        user = CustomUser.objects.create_user(
            email="user@email.com",
            username="user",
            password=make_password("password"),
            email_notifications_left=1,
        )
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            user=user,
            notification_type="email",
            notification_retries_left=1,
        )
        mocker.patch(
            "core.tasks.build_notification_title_and_text",
            return_value=("mock_title", "mock_text"),
        )
        mocked_send_email_func = mocker.patch("core.tasks.send_mail", return_value=0)
        mocked_decrement_func = mocker.patch("core.tasks.decrement_notifications_left")

        result = send_notification(event)

        assert result == False
        mocked_send_email_func.assert_called_once()
        mocked_decrement_func.assert_not_called()
        assert event.notification_retries_left == 0

    def test_send_notification_failed_out_of_retries(self, mocker):
        user = CustomUser.objects.create_user(
            email="user@email.com",
            username="user",
            password=make_password("password"),
            email_notifications_left=1,
        )
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            user=user,
            notification_type="email",
            notification_retries_left=0,
        )
        mocker.patch(
            "core.tasks.build_notification_title_and_text",
            return_value=("mock_title", "mock_text"),
        )
        mocked_send_email_func = mocker.patch("core.tasks.send_mail", return_value=0)
        mocked_decrement_func = mocker.patch("core.tasks.decrement_notifications_left")

        result = send_notification(event)

        assert result == True
        mocked_send_email_func.assert_called_once()
        mocked_decrement_func.assert_not_called()
        assert event.notification_retries_left == 0


class TestTasks(TestCase):
    """Test suite for Celery tasks"""

    def setUp(self):
        self.current_datetime = datetime(
            2020, 1, 1, 10, 5, tzinfo=timezone.utc
        )  # 2020-01-01 10:05
        self.current_timestamp = int(self.current_datetime.timestamp())
        self.user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )

    def test_get_new_date_and_time(self):
        result = get_new_date_and_time(
            "2020-01-01", "10:00", "30min", "+0", self.current_timestamp
        )
        expected_result = ("2020-01-01", "10:30")
        self.assertEqual(result, expected_result)

    def test_reschedule_or_delete_event_without_interval(self):
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            user=self.user,
        )
        self.assertEqual(Event.objects.count(), 1)
        reschedule_or_delete_event(
            event, self.current_timestamp
        )  # Event should be deleted
        self.assertEqual(Event.objects.count(), 0)

    def test_reschedule_or_delete_event_with_interval(self):
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            interval="30min",
            utc_offset="+0",
            user=self.user,
        )
        reschedule_or_delete_event(
            event, self.current_timestamp
        )  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_reschedule_or_delete_event_with_interval_missed_timestamp(self):
        event = Event.objects.create(
            title=f"Title-1",
            date="2019-01-01",
            time="10:00",
            interval="30min",
            utc_offset="+0",
            user=self.user,
        )
        reschedule_or_delete_event(
            event, self.current_timestamp
        )  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

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
        reset_notifications_left()
        self.assertEqual(
            CustomUser.objects.get(username="reset").email_notifications_left,
            settings.NO_OF_FREE_EMAIL_NOTIFICATIONS,
        )
        self.assertEqual(
            CustomUser.objects.get(username="reset").sms_notifications_left,
            settings.NO_OF_FREE_SMS_NOTIFICATIONS,
        )

    def test_decrement_notifications_left(self):
        user = CustomUser.objects.create_user(
            email="decrement@email.com",
            username="decrement",
            password=make_password("password"),
            email_notifications_left=10,
        )
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            user=user,
            notification_type="email",
        )
        result = decrement_notifications_left(event)
        self.assertEqual(result, True)
        self.assertEqual(
            CustomUser.objects.get(username="decrement").email_notifications_left, 9
        )

    def test_decrement_notifications_left_on_last_notification(self):
        user = CustomUser.objects.create_user(
            email="decrement2@email.com",
            username="decrement2",
            password=make_password("password"),
            email_notifications_left=1,
        )
        event = Event.objects.create(
            title=f"Title-1",
            date="2020-01-01",
            time="10:00",
            utc_offset="+0",
            user=user,
            notification_type="email",
        )
        result = decrement_notifications_left(event)
        self.assertEqual(result, False)
        self.assertEqual(
            CustomUser.objects.get(username="decrement2").email_notifications_left, 0
        )


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
