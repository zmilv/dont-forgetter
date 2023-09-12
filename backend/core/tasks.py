import logging
import os
from datetime import datetime, timedelta, timezone

import requests
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from core.models import Event, apply_utc_offset, parse_notice_time_or_interval
from users.models import CustomUser

logger = logging.getLogger(__name__)

vonage_api_key = os.environ.get("VONAGE_API_KEY")
vonage_api_secret = os.environ.get("VONAGE_API_SECRET")


def decrement_notifications_left(event):
    result = True
    notification_type = event.notification_type
    notifications_left = getattr(event.user, f"{notification_type}_notifications_left")
    if notifications_left == 1:
        logger.info(f"Event {event} rejected due to notification limit")
        notification_limit_message = (
            f"Unfortunately you have no {notification_type} notifications left for this"
            f" month. Please contact {settings.CONTACT_EMAIL} if you would like to have this"
            f" limit lifted.{settings.MESSAGE_SIGNATURE}"
        )
        send_email_args_dict = {
            "title": f"{notification_type} notification limit reached".capitalize(),
            "text": notification_limit_message,
            "email": event.user.email,
        }
        send_email(send_email_args_dict)
        result = False
    notifications_left -= 1
    setattr(
        event.user, f"{event.notification_type}_notifications_left", notifications_left
    )
    event.user.save()
    return result


def send_sms(args_dict):
    with requests.Session() as session:
        phone_number = args_dict["phone_number"]
        text = args_dict["text"]
        url = "https://rest.nexmo.com/sms/json"
        params = {
            "api_key": vonage_api_key,
            "api_secret": vonage_api_secret,
            "from": "dont-forgetter",
            "to": phone_number,
            "text": text,
        }
        response = session.post(url, data=params)
        logger.info(f"SMS response: {response.json()}")
        if response.json()["messages"][0]["status"] == "0":
            logger.info(f"SMS sent")
            return True
        else:
            logger.warning("SMS sending failed")
            return False


def send_email(args_dict):
    title = args_dict["title"]
    text = args_dict["text"]
    email = args_dict["email"]

    result = send_mail(title, text, None, [email], fail_silently=False)
    if result == 1:
        logger.info("E-mail sent")
        return True
    logger.warning("E-mail sending failed")
    return False


class NotificationContents:
    def __init__(self, event):
        self.event = event
        if event.custom_variables:
            self.variable_dict = self.parse_custom_message_variables()

        self.email_title = self.get_email_title()
        self.message = self.get_message()

    def parse_custom_message_variables(self):
        """
        Takes the custom_variables and returns a dictionary of the variables.
        Example of custom_variables: 'name=Tom; surname=Smith'.
        Example of output: {'name': 'Tom', 'surname': 'Smith'}.
        """
        variables_dict = {}
        variables_list = self.event.custom_variables.split(";")
        for variable in variables_list:
            variable_split = variable.split("=")
            variables_dict[variable_split[0].strip()] = variable_split[1]
        return variables_dict

    def build_custom_text(self, template, variable_dict):
        """
        Takes the template and replaces the plugs the variables in.
        Example of template: 'hi {{name}}, your last name is {{surname}}'.
        Example of output: 'hi Tom, your last name is Smith'.
        """
        for key, value in variable_dict.items():
            template = template.replace("{{" + key + "}}", value)
        return template

    def build_default_title(self):
        notification_title = f"Time for {self.event.title}"
        if self.event.category != "other":
            notification_title += f" ({self.event.category})"
        notification_title += "!"

        return notification_title

    def build_default_message(self):
        notification_text = f"It is time for {self.event.title}"
        if self.event.category != "other":
            notification_text += f" ({self.event.category})"
        if self.event.notice_time != "-":
            notification_text += f" in {self.event.notice_time}"
        notification_text += "."
        notification_text += f"\n(Scheduled for {self.event.date} {self.event.time} UTC{self.event.utc_offset})"
        if self.event.interval != "-":
            notification_text += f"\nNext such event scheduled in {self.event.interval}."
        if self.event.info:
            notification_text += f"\nInfo: {self.event.info}"
        notification_text += settings.MESSAGE_SIGNATURE

        return notification_text

    def get_message(self):
        if not self.event.custom_message:
            return self.build_default_message()
        elif self.event.custom_variables:
            return self.build_custom_text(self.event.custom_message, self.variable_dict)
        return self.event.custom_message

    def get_email_title(self):
        if not self.event.custom_email_title:
            return self.build_default_title()
        elif self.event.custom_variables:
            return self.build_custom_text(self.event.custom_email_title, self.variable_dict)
        return self.event.custom_email_title


notification_funcs = {"email": send_email, "sms": send_sms}


def send_notification(event):
    notification_type = event.notification_type
    if getattr(event.user, f"{notification_type}_notifications_left") > 0:
        logger.info(f"{event} - Sending notification")
        logger.info(f"{event.date} {event.time}")
        notification_contents = NotificationContents(event)
        args_dict = {
            "title": notification_contents.email_title,
            "text": notification_contents.message,
            "email": event.user.email,
            "phone_number": event.user.phone_number,
        }
        notification_func = notification_funcs[notification_type]
        notification_sent = notification_func(args_dict)
        if notification_sent:
            if not event.user.premium_member:
                decrement_notifications_left(event)
                return True
        else:
            if event.notification_retries_left > 0:
                event.notification_retries_left -= 1
                event.save()
                return False
            return True
    return True


def get_new_date_and_time(
    old_date, old_time, interval, utc_offset, current_utc_timestamp
):
    current_datetime = datetime.fromtimestamp(current_utc_timestamp, tz=timezone.utc)
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


def reschedule_event(event, current_utc_timestamp):
    logger.info(f"{event} - Rescheduling")
    new_date, new_time = get_new_date_and_time(
        event.date, event.time, event.interval, event.utc_offset, current_utc_timestamp
    )
    event.date = new_date
    event.time = new_time
    logger.info(f"New: {event.date} {event.time}")
    event.notification_retries_left = settings.MAX_NOTIFICATION_RETRIES
    event.save()


def reschedule_or_delete_event(event, current_utc_timestamp):
    if event.interval == "-":
        logger.info(f"{event} - Deleting")
        event.delete()
    else:
        reschedule_event(event, current_utc_timestamp)


@shared_task()
def send_notification_and_reschedule_or_delete_event(event_pk, current_utc_timestamp):
    try:
        event = Event.objects.get(pk=event_pk)
        not_to_be_retried = send_notification(event)
        if not_to_be_retried:
            reschedule_or_delete_event(event, current_utc_timestamp)
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
            task_id = send_notification_and_reschedule_or_delete_event.delay(
                event.pk, current_utc_timestamp
            ).id
            result.append(task_id)
        return result
    except Exception as e:
        logger.exception(e)
        raise


@shared_task()
def reset_notifications_left():
    CustomUser.objects.all().update(
        email_notifications_left=settings.NO_OF_FREE_EMAIL_NOTIFICATIONS,
        sms_notifications_left=settings.NO_OF_FREE_SMS_NOTIFICATIONS,
    )
