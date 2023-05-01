from django.test import TestCase
from core.tasks import get_new_date_and_time, reschedule_or_delete_event, heartbeat
from core.models import Event
from datetime import datetime, timezone


class TestTasks(TestCase):
    """ Test suite for Celery tasks """

    def setUp(self):
        self.current_datetime = datetime(2024, 1, 1, 10, 5, tzinfo=timezone.utc)  # 2024-01-01 10:05
        self.current_timestamp = int(self.current_datetime.timestamp())

    def test_get_new_date_and_time(self):
        result = get_new_date_and_time('2024-01-01', '10:00', '30min', self.current_timestamp)
        expected_result = ('2024-01-01', '10:30')
        self.assertEqual(result, expected_result)

    def test_reschedule_or_delete_event_without_interval(self):
        event = Event.objects.create(title=f'Title-1', date='2024-01-01', time='10:00')
        self.assertEqual(Event.objects.count(), 1)
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be deleted
        self.assertEqual(Event.objects.count(), 0)

    def test_reschedule_or_delete_event_with_interval(self):
        event = Event.objects.create(title=f'Title-1', date='2024-01-01', time='10:00', interval='30min')
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2024-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_reschedule_or_delete_event_with_interval_missed_timestamp(self):
        event = Event.objects.create(title=f'Title-1', date='2023-01-01', time='10:00', interval='30min')
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2024-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    # @patch('core.tasks.current_datetime', return_value=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc))
    # @patch('core.tasks.heartbeat.datetime.now', return_value=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc))
    # def test_heartbeat_with_interval(self):
    #     Event.objects.create(title=f'Title-1', date='2022-01-01', interval='30min')
    #     # with patch('celeryconfig.CELERY_ALWAYS_EAGER', True, create=True):
    #     heartbeat.apply()
    #     self.assertEqual(Event.objects.count(), 1)
    #     self.assertEqual(Event.objects.get().title, "Title-1")
    #     self.assertEqual(Event.objects.get().date, "2022-01-01")
    #     self.assertEqual(Event.objects.get().time, "10:30")


# class TestHeartbeat:
#     @pytest.fixture(scope='session')
#     def celery_config():
#         return {
#             'broker_url': 'amqp://',
#             'result_backend': 'redis://'
#         }

    # @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
    # def test_heartbeat_with_interval(self):
    #     Event.objects.create(title=f'Title-1', date='2022-01-01', interval='30min')
    #     heartbeat()
    #     self.assertEqual(Event.objects.count(), 1)
    #     self.assertEqual(Event.objects.get().title, "Title-1")
    #     self.assertEqual(Event.objects.get().date, "2022-01-01")
    #     self.assertEqual(Event.objects.get().time, "10:30")