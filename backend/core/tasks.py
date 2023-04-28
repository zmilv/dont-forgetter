from celery import shared_task
from core.models import Event, parse_notice_time_or_interval
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task()
def send_notification(event_pk):
    event = Event.objects.get(pk=event_pk)
    logger.info(f'ID{event.pk} - Sending notification')


def get_new_date_and_time(old_date, old_time, interval):
    datetime_str = f'{old_date} {old_time}'
    datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
    datetime_object += timedelta(**parse_notice_time_or_interval(interval))
    datetime_str = datetime.strftime(datetime_object, '%Y-%m-%d %H:%M')
    new_date = datetime_str[:10]
    new_time = datetime_str[-5:]
    return new_date, new_time


@shared_task()
def reschedule_or_delete_event(event_pk):
    event = Event.objects.get(pk=event_pk)
    if event.interval == '-':
        logger.info(f'ID{event.pk} - Deleting')
        event.delete()
    else:
        logger.info(f'ID{event.pk} - Rescheduling')
        new_date, new_time = get_new_date_and_time(event.date, event.time, event.interval)
        event.date = new_date
        event.time = new_time
        event.save()


@shared_task()
def heartbeat():
    current_datetime = datetime.now(timezone.utc)
    current_utc_timestamp = int(current_datetime.timestamp())
    logger.info(f'HEARTBEAT. UTC: {current_utc_timestamp}')
    expired_events = Event.objects.filter(utc_timestamp__lt=current_utc_timestamp)
    for event in expired_events:
        logger.info(f'ID{event.pk} {event.title}({event.type}) - Expired')
        send_notification.delay(event.pk)
        reschedule_or_delete_event.delay(event.pk)
