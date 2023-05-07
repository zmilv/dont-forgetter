from django.test import TestCase, SimpleTestCase
from core.tasks import get_new_date_and_time, reschedule_or_delete_event, heartbeat
from core.models import Event
from datetime import datetime, timezone
from unittest import mock


class TestTasks(TestCase):
    """ Test suite for Celery tasks """

    def setUp(self):
        self.current_datetime = datetime(2020, 1, 1, 10, 5, tzinfo=timezone.utc)  # 2020-01-01 10:05
        self.current_timestamp = int(self.current_datetime.timestamp())
        # Start patcher
        self.patcher = mock.patch('core.tasks.datetime')
        self.patcher.now = mock.Mock(return_value=self.current_datetime)
        self.patcher.side_effect = lambda *args, **kw: datetime(*args, **kw)

    def tearDown(self):
        self.patcher.stop()  # Stop patcher

    def test_get_new_date_and_time(self):
        result = get_new_date_and_time('2020-01-01', '10:00', '30min', self.current_timestamp)
        expected_result = ('2020-01-01', '10:30')
        self.assertEqual(result, expected_result)

    def test_reschedule_or_delete_event_without_interval(self):
        event = Event.objects.create(title=f'Title-1', date='2020-01-01', time='10:00')
        self.assertEqual(Event.objects.count(), 1)
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be deleted
        self.assertEqual(Event.objects.count(), 0)

    def test_reschedule_or_delete_event_with_interval(self):
        event = Event.objects.create(title=f'Title-1', date='2020-01-01', time='10:00', interval='30min')
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")

    def test_reschedule_or_delete_event_with_interval_missed_timestamp(self):
        event = Event.objects.create(title=f'Title-1', date='2019-01-01', time='10:00', interval='30min')
        reschedule_or_delete_event(event.pk, self.current_timestamp)  # Event should be updated
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.get().title, "Title-1")
        self.assertEqual(Event.objects.get().date, "2020-01-01")
        self.assertEqual(Event.objects.get().time, "10:30")
