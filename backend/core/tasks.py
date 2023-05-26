import logging
from datetime import datetime, timedelta, timezone

from celery import chain, shared_task
from django.core.mail import send_mail

from core.models import Event, parse_notice_time_or_interval

logger = logging.getLogger(__name__)


@shared_task()
def send_windows_popup(title, text):  # For local development only
    import ctypes
    import winsound

    winsound.Beep(440, 1000)  # 440Hz, 1000ms
    ctypes.windll.user32.MessageBoxW(0, text, title, 0)
    return None


@shared_task()
def send_email(title, text, email):
    try:
        send_mail(title, text, None, [email], fail_silently=False)
        return None
    except Exception as e:
        logger.exception(e)
        raise


def build_notification_text(event):
    notification_text = f"It is time for {event.title} ({event.type})"
    if event.notice_time != "-":
        notification_text += f" in {event.notice_time}"
    notification_text += "."
    if event.interval != "-":
        notification_text += f" Next such event scheduled in {event.interval}."
    if event.info:
        notification_text += f" Info: {event.info}"
    return notification_text


@shared_task()
def send_notification(event_pk):
    try:
        event = Event.objects.get(pk=event_pk)
        logger.info(f"{event} - Sending notification")
        logger.info(f"{event.date} {event.time}")
        notification_title = f"Time for {event.title} ({event.type}) !"
        notification_text = build_notification_text(event)
        # send_windows_popup.delay(notification_title, notification_text)
        send_email.delay(notification_title, notification_text, event.user.email)
        return None
    except Exception as e:
        logger.exception(e)
        raise


def get_new_date_and_time(old_date, old_time, interval, current_utc_timestamp):
    current_datetime = datetime.fromtimestamp(current_utc_timestamp, tz=timezone.utc)
    try:
        datetime_str = f"{old_date} {old_time}"
        datetime_object = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(
            tzinfo=timezone.utc
        )
        while datetime_object < current_datetime:
            datetime_object += timedelta(**parse_notice_time_or_interval(interval))
        datetime_str = datetime.strftime(datetime_object, "%Y-%m-%d %H:%M")
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
        if event.interval == "-":
            logger.info(f"{event} - Deleting")
            event.delete()
        else:
            logger.info(f"{event} - Rescheduling")
            new_date, new_time = get_new_date_and_time(
                event.date, event.time, event.interval, current_utc_timestamp
            )
            event.date = new_date
            event.time = new_time
            logger.info(f"New: {event.date} {event.time}")
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
        logger.info(f"HEARTBEAT. UTC: {current_utc_timestamp}")
        expired_events = Event.objects.filter(utc_timestamp__lt=current_utc_timestamp)
        for event in expired_events:
            logger.info(f"{event} - Expired")
            chain_result = chain(
                send_notification.si(event.pk)
                | reschedule_or_delete_event.si(event.pk, current_utc_timestamp)
            )()
            return chain_result.as_list()
        return []
    except Exception as e:
        logger.exception(e)
        raise
