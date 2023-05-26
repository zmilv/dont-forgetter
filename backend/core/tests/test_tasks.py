from django.test import TestCase, SimpleTestCase
from core.tasks import get_new_date_and_time, reschedule_or_delete_event, heartbeat
from core.models import Event
from datetime import datetime, timezone
from backend.celery import app
from celery.contrib.testing.worker import start_worker
from celery.result import AsyncResult
from freezegun import freeze_time
from users.models import CustomUser
from django.contrib.auth.hashers import make_password


class TestTasks(TestCase):
    """ Test suite for Celery tasks """

    def setUp(self):
        self.current_datetime = datetime(2020, 1, 1, 10, 5, tzinfo=timezone.utc)  # 2020-01-01 10:05
        self.current_timestamp = int(self.current_datetime.timestamp())
        self.user = CustomUser.objects.create_user(
            email='email@email.com',
            username='name',
            password=make_password('password')
        )

    def test_get_new_date_and_time(self):
        result = get_new_date_and_time('2020-01-01', '10:00', '30min', self.current_timestamp)
        expected_result = ('2020-01-01', '10:30')
        self.assertEqual(result, expected_result)

    def test_reschedule_or_delete_event_without_interval(self):
        event = Event.objects.create(title=f'Title-1', date='2020-01-01', time='10:00', user=self.user)
        self.assertEqual(Event.objects.count(), 1)
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be deleted
        self.assertEqual(Event.objects.count(), 0)

    def test_reschedule_or_delete_event_with_interval(self):
        event = Event.objects.create(title=f'Title-1', date='2020-01-01', time='10:00', interval='30min',
                                     user=self.user)
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_reschedule_or_delete_event_with_interval_missed_timestamp(self):
        event = Event.objects.create(title=f'Title-1', date='2019-01-01', time='10:00', interval='30min',
                                     user=self.user)
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")


@freeze_time('2020-01-01 10:05')  # Mocks current datetime
class TestCeleryIntegration(SimpleTestCase):
    databases = '__all__'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = CustomUser.objects.create_user(
            email='email@email.com',
            username='name',
            password=make_password('password')
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
        Event.objects.create(title=f'Title-1', date='2020-01-01', time='10:00', user=self.user)
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should be deleted
        result = heartbeat_task.get()
        reschedule_or_delete_id, send_notification_id = result[0], result[1]
        send_notification_task = AsyncResult(send_notification_id, app=app)
        reschedule_or_delete_task = AsyncResult(reschedule_or_delete_id, app=app)
        send_notification_task.get()
        reschedule_or_delete_task.get()
        self.assertEqual(heartbeat_task.status, 'SUCCESS')
        self.assertEqual(send_notification_task.status, 'SUCCESS')
        self.assertEqual(reschedule_or_delete_task.status, 'SUCCESS')
        self.assertEqual(Event.objects.count(), 0)

    def test_heartbeat_with_interval(self):
        Event.objects.create(title=f'Title-1', date='2020-01-01', time='10:00', interval='30min', user=self.user)
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should be updated
        result = heartbeat_task.get()
        reschedule_or_delete_id, send_notification_id = result[0], result[1]
        send_notification_task = AsyncResult(send_notification_id, app=app)
        reschedule_or_delete_task = AsyncResult(reschedule_or_delete_id, app=app)
        send_notification_task.get()
        reschedule_or_delete_task.get()
        self.assertEqual(heartbeat_task.status, 'SUCCESS')
        self.assertEqual(send_notification_task.status, 'SUCCESS')
        self.assertEqual(reschedule_or_delete_task.status, 'SUCCESS')
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_heartbeat_with_missed_timestamp(self):
        Event.objects.create(title=f'Title-1', date='2019-01-01', time='10:00', interval='30min', user=self.user)
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should be updated
        result = heartbeat_task.get()
        reschedule_or_delete_id, send_notification_id = result[0], result[1]
        send_notification_task = AsyncResult(send_notification_id, app=app)
        reschedule_or_delete_task = AsyncResult(reschedule_or_delete_id, app=app)
        send_notification_task.get()
        reschedule_or_delete_task.get()
        self.assertEqual(heartbeat_task.status, 'SUCCESS')
        self.assertEqual(send_notification_task.status, 'SUCCESS')
        self.assertEqual(reschedule_or_delete_task.status, 'SUCCESS')
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_heartbeat_without_expired_events(self):
        Event.objects.create(title=f'Title-1', date='2020-01-01', time='11:00', user=self.user)
        self.assertEqual(Event.objects.count(), 1)
        heartbeat_task = heartbeat.delay()  # Event should remain unchanged
        result = heartbeat_task.get()
        self.assertEqual(result, [])
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "11:00")
