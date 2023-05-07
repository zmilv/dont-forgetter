from celery import shared_task, chain
from core.models import Event, parse_notice_time_or_interval
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task()
def send_notification(event_pk):
    try:
        event = Event.objects.get(pk=event_pk)
        logger.info(f'{event} - Sending notification')
        logger.info(f'{event.date} {event.time}')
        return None
    except Exception as e:
        logger.exception(e)
        raise


def get_new_date_and_time(old_date, old_time, interval, current_utc_timestamp):
    current_datetime = datetime.fromtimestamp(current_utc_timestamp, tz=timezone.utc)
    try:
        datetime_str = f'{old_date} {old_time}'
        datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
        while datetime_object < current_datetime:
            datetime_object += timedelta(**parse_notice_time_or_interval(interval))
        datetime_str = datetime.strftime(datetime_object, '%Y-%m-%d %H:%M')
        new_date = datetime_str[:10]
        new_time = datetime_str[-5:]
        return new_date, new_time
    except Exception as e:
        logger.exception(e)
        raise


@shared_task()
def reschedule_or_delete_event(event_pk, current_utc_timestamp):
    try:
        event = Event.objects.get(pk=event_pk)
        if event.interval == '-':
            logger.info(f'{event} - Deleting')
            event.delete()
        else:
            logger.info(f'{event} - Rescheduling')
            new_date, new_time = get_new_date_and_time(event.date, event.time, event.interval, current_utc_timestamp)
            event.date = new_date
            event.time = new_time
            logger.info(f'New: {event.date} {event.time}')
            event.save()
            return None
    except Exception as e:
        logger.exception(e)
        raise


@shared_task()
def heartbeat():
    try:
        current_datetime = datetime.now(timezone.utc)
        current_utc_timestamp = int(current_datetime.timestamp())
        logger.info(f'HEARTBEAT. UTC: {current_utc_timestamp}')
        expired_events = Event.objects.filter(utc_timestamp__lt=current_utc_timestamp)
        for event in expired_events:
            logger.info(f'{event} - Expired')
            chain_result = \
                chain(send_notification.si(event.pk) | reschedule_or_delete_event.si(event.pk, current_utc_timestamp))()
            return chain_result.as_list()
        return None
    except Exception as e:
        logger.exception(e)
        raise
