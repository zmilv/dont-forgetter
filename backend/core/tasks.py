import logging
import os
from abc import ABC, abstractmethod
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


class NotificationStrategy(ABC):
    def __init__(self, event):
        self.event = event
        if event.custom_variables:
            self.variable_dict = self.parse_custom_message_variables()
        self.message = self.get_message()

    @abstractmethod
    def send_notification(self):
        pass

    def get_message(self):
        if not self.event.custom_message:
            return self.build_default_message()
        elif self.event.custom_variables:
            return self.build_custom_text(self.event.custom_message, self.variable_dict)
        return self.event.custom_message

    def build_custom_text(self, template, variable_dict):
        """
        Takes the template and replaces the plugs the variables in.
        Example of template: 'hi {{name}}, your last name is {{surname}}'.
        Example of output: 'hi Tom, your last name is Smith'.
        """
        for key, value in variable_dict.items():
            template = template.replace("{{" + key + "}}", value)
        return template

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

    def build_default_message(self):
        notification_text = f"It is time for {self.event.title}"
        if self.event.category != "other":
            notification_text += f" ({self.event.category})"
        if self.event.notice_time != "-":
            notification_text += f" in {self.event.notice_time}"
        notification_text += "."
        notification_text += f"\n(Scheduled for {self.event.date} {self.event.time} UTC{self.event.utc_offset})"
        if self.event.interval != "-":
            notification_text += (
                f"\nNext such event scheduled in {self.event.interval}."
            )
        notification_text += settings.MESSAGE_SIGNATURE

        return notification_text


class EmailNotification(NotificationStrategy):
    def __init__(self, event):
        super().__init__(event)
        self.email_title = self.get_email_title()

    def send_notification(self):
        result = send_mail(
            self.email_title,
            self.message,
            None,
            [self.event.recipient],
            fail_silently=False,
        )
        if result == 1:
            logger.info("E-mail sent")
            return True
        logger.warning("E-mail sending failed")
        return False

    def get_email_title(self):
        if not self.event.custom_email_subject:
            return self.build_default_title()
        elif self.event.custom_variables:
            return self.build_custom_text(
                self.event.custom_email_subject, self.variable_dict
            )
        return self.event.custom_email_subject

    def build_default_title(self):
        notification_title = f"Time for {self.event.title}"
        if self.event.category != "other":
            notification_title += f" ({self.event.category})"
        notification_title += "!"
        return notification_title


class SMSNotification(NotificationStrategy):
    def __init__(self, event):
        super().__init__(event)

    def send_notification(self):
        with requests.Session() as session:
            url = "https://rest.nexmo.com/sms/json"
            params = {
                "api_key": vonage_api_key,
                "api_secret": vonage_api_secret,
                "from": self.event.user.usersettings.sms_sender_name,
                "to": self.event.recipient,
                "text": self.message,
            }
            response = session.post(url, data=params)
            logger.info(f"SMS response: {response.json()}")
            if response.json()["messages"][0]["status"] == "0":
                logger.info(f"SMS sent")
                return True
            else:
                logger.warning("SMS sending failed")
                return False


class NotificationService:
    def __init__(self, event):
        self.event = event
        if self.event.notification_type == "email":
            strategy = EmailNotification
        elif self.event.notification_type == "sms":
            strategy = SMSNotification
        else:
            raise ValueError("Invalid notification preference")
        self.strategy = strategy(self.event)

    def send_notification(self):
        if (
            getattr(
                self.event.user, f"{self.event.notification_type}_notifications_left"
            )
            > 0
        ):
            logger.info(f"{self.event} - Sending notification")
            logger.info(f"{self.event.date} {self.event.time}")

            notification_sent = self.strategy.send_notification()
            if notification_sent:
                if self.event.interval != "-" and self.event.count:
                    self.event.count -= 1
                    self.event.save()
                if not self.event.user.premium_member:
                    self.decrement_notifications_left()
                    return True
            else:
                if self.event.notification_retries_left > 0:
                    self.event.notification_retries_left -= 1
                    self.event.save()
                    return False
                return True
        return True

    def decrement_notifications_left(self):
        result = True
        notifications_left = getattr(
            self.event.user, f"{self.event.notification_type}_notifications_left"
        )
        if notifications_left == 1:
            logger.info(f"Event {self.event} rejected due to notification limit")
            self.send_notification_limit_email()
            result = False
        notifications_left -= 1
        setattr(
            self.event.user,
            f"{self.event.notification_type}_notifications_left",
            notifications_left,
        )
        self.event.user.save()
        return result

    def send_notification_limit_email(self):
        notification_limit_message = (
            f"Unfortunately you have no {self.event.notification_type} notifications left for this"
            f" month. Please contact {settings.CONTACT_EMAIL} if you would like to have this"
            f" limit lifted.{settings.MESSAGE_SIGNATURE}"
        )
        email_title = (
            f"{self.event.notification_type} notification limit reached".capitalize()
        )
        result = send_mail(
            email_title,
            notification_limit_message,
            None,
            self.event.user.email,
            fail_silently=False,
        )
        if result == 1:
            logger.info("Notification limit e-mail sent")
        logger.warning("Notification limit e-mail sending failed")


class NotificationEvent:
    def __init__(self, event, current_utc_timestamp):
        self.event = event
        self.current_utc_timestamp = current_utc_timestamp

    def reschedule_or_delete_event(self):
        if self.event.interval == "-" or self.event.count == 0:
            logger.info(f"{self.event} - Deleting")
            self.event.delete()
        else:
            self.reschedule_event()

    def reschedule_event(self):
        logger.info(f"{self.event} - Rescheduling")
        new_date, new_time = self.get_new_date_and_time()
        self.event.date = new_date
        self.event.time = new_time
        logger.info(f"New: {self.event.date} {self.event.time}")
        self.event.notification_retries_left = settings.MAX_NOTIFICATION_RETRIES
        self.event.save()

    def get_new_date_and_time(self):
        current_datetime = datetime.fromtimestamp(
            self.current_utc_timestamp, tz=timezone.utc
        )
        datetime_str = f"{self.event.date} {self.event.time}"
        datetime_object = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(
            tzinfo=timezone.utc
        )
        datetime_object = apply_utc_offset(self.event.utc_offset, datetime_object)
        while datetime_object < current_datetime:
            datetime_object += timedelta(
                **parse_notice_time_or_interval(self.event.interval)
            )
        datetime_object = apply_utc_offset(
            self.event.utc_offset, datetime_object, reverse=True
        )
        datetime_str = datetime.strftime(datetime_object, "%Y-%m-%d %H:%M")
        new_date = datetime_str[:10]
        new_time = datetime_str[-5:]
        return new_date, new_time


@shared_task()
def send_notification_and_reschedule_or_delete_event(event_pk, current_utc_timestamp):
    try:
        event = Event.objects.get(pk=event_pk)
        not_to_be_retried = NotificationService(event).send_notification()
        if not_to_be_retried:
            NotificationEvent(event, current_utc_timestamp).reschedule_or_delete_event()
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
