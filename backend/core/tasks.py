import logging
import os
from datetime import datetime, timedelta, timezone

import requests
from celery import chain, shared_task
from django.core.mail import send_mail
from django.conf import settings

from core.models import Event, parse_notice_time_or_interval
from users.models import CustomUser

logger = logging.getLogger(__name__)

api_key = os.environ.get("VONAGE_API_KEY")
api_secret = os.environ.get("VONAGE_API_SECRET")


def decrement_notifications_left(event):
    notification_type = event.notification_type
    notifications_left = getattr(event.user, f"{notification_type}_notifications_left")
    if notifications_left == 1:
        logger.info(f"Event {event} rejected due to notification limit")
        notification_limit_message = f"Unfortunately you have no {notification_type} notifications left for this" \
                                     f" month. Please contact {settings.CONTACT_EMAIL} if you would like to have this" \
                                     f" limit lifted.{settings.MESSAGE_SIGNATURE}"
        send_email_args_dict = {
            "title": f"{notification_type} notification limit reached".capitalize(),
            "text": notification_limit_message,
            "email": event.user.email
        }
        send_email.delay(send_email_args_dict)
    notifications_left -= 1
    setattr(event.user, f"{event.notification_type}_notifications_left", notifications_left)
    event.user.save()


@shared_task()
def send_sms(args_dict):
    try:
        with requests.Session() as session:
            phone_number = args_dict["phone_number"]
            text = args_dict["text"]
            url = "https://rest.nexmo.com/sms/json"
            params = {
                "api_key": api_key,
                "api_secret": api_secret,
                "from": "dont-forgetter",
                "to": phone_number,
                "text": text,
            }
            response = session.post(url, data=params)
            logger.info(f"SMS response: {response.json()}")
            return None
    except Exception as e:
        logger.exception(e)
        raise


@shared_task()
def send_email(args_dict):
    title = args_dict["title"]
    text = args_dict["text"]
    email = args_dict["email"]
    try:
        result = send_mail(title, text, None, [email], fail_silently=False)
        logger.info("E-mail sent") if result == 1 else logger.warning(
            "E-mail sending failed"
        )
        return result
    except Exception as e:
        logger.exception(e)
        raise


def build_notification_title_and_text(event):
    category = event.category
    title = event.title
    date = event.date
    time = event.time
    notice_time = event.notice_time
    interval = event.interval
    info = event.info

    notification_title = f"Time for {title}"
    if category != "other":
        notification_title += f" ({category})"
    notification_title += "!"

    notification_text = f"It is time for {title}"
    if category != "other":
        notification_text += f" ({category})"
    if notice_time != "-":
        notification_text += f" in {notice_time}"
    notification_text += "."
    notification_text += f"\n(Scheduled for {date} {time})"
    if interval != "-":
        notification_text += f"\nNext such event scheduled in {interval}."
    if info:
        notification_text += f"\nInfo: {info}"
    notification_text += settings.MESSAGE_SIGNATURE

    return notification_title, notification_text


notification_funcs = {"email": send_email, "sms": send_sms}


@shared_task()
def send_notification(event_pk):
    try:
        event = Event.objects.get(pk=event_pk)
        notification_type = event.notification_type
        if getattr(event.user, f"{notification_type}_notifications_left") > 0:
            logger.info(f"{event} - Sending notification")
            logger.info(f"{event.date} {event.time}")
            notification_title, notification_text = build_notification_title_and_text(event)
            args_dict = {
                "title": notification_title,
                "text": notification_text,
                "email": event.user.email,
                "phone_number": event.user.phone_number,
            }
            notification_func = notification_funcs[notification_type]
            notification_func.delay(args_dict)
        decrement_notifications_left(event)
        return None
    except Exception as e:
        logger.exception(e)
        raise


def get_new_date_and_time(old_date, old_time, interval, utc_offset, current_utc_timestamp):
    current_datetime = datetime.fromtimestamp(current_utc_timestamp, tz=timezone.utc)
    try:
        datetime_str = f"{old_date} {old_time}"
        datetime_object = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(
            tzinfo=timezone.utc
        )
        datetime_object = apply_utc_offset(utc_offset, datetime_object)
        while datetime_object < current_datetime:
            datetime_object += timedelta(**parse_notice_time_or_interval(interval))
        datetime_object = apply_utc_offset(utc_offset, datetime_object, reverse=True)
        datetime_str = datetime.strftime(datetime_object, "%Y-%m-%d %H:%M")
        new_date = datetime_str[:10]
        new_time = datetime_str[-5:]
        return new_date, new_time
    except Exception as e:
        logger.exception(e)
        raise


def reschedule_event(event, current_utc_timestamp):
    logger.info(f"{event} - Rescheduling")
    new_date, new_time = get_new_date_and_time(
        event.date, event.time, event.interval, event.utc_offset, current_utc_timestamp
    )
    event.date = new_date
    event.time = new_time
    logger.info(f"New: {event.date} {event.time}")
    event.save()


@shared_task()
def reschedule_or_delete_event(event_pk, current_utc_timestamp):
    try:
        event = Event.objects.get(pk=event_pk)
        if event.interval == "-":
            logger.info(f"{event} - Deleting")
            event.delete()
        else:
            reschedule_event(event, current_utc_timestamp)
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
        result = []
        for event in expired_events:
            logger.info(f"{event} - Expired")
            chain_result = chain(
                send_notification.si(event.pk)
                | reschedule_or_delete_event.si(event.pk, current_utc_timestamp)
            )()
            result.append(chain_result.as_list())
        return result
    except Exception as e:
        logger.exception(e)
        raise


@shared_task()
def reset_notifications_left():
    CustomUser.objects.all().update(email_notifications_left=settings.NO_OF_FREE_EMAIL_NOTIFICATIONS,
                                    sms_notifications_left=settings.NO_OF_FREE_SMS_NOTIFICATIONS)
