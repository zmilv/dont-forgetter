import re
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import models
from rest_framework import serializers

from core.validators import (
    date_validator,
    interval_and_notice_validator,
    notification_type_validator,
    time_validator,
    units_translation_dict,
    utc_offset_validator,
)
from users.models import UserSettings


def get_utc_offset(local_date):  # Unused. Todo: derive from user location setting
    datetime_object = datetime.strptime(local_date, "%Y-%m-%d")
    local_timezone = datetime_object.astimezone()
    offset = local_timezone.utcoffset() // timedelta(minutes=1) / 60
    hours = int(offset)
    mins = int(offset % 1 * 60)
    if mins:
        result = f"{hours}:{mins}"
    else:
        result = f"{hours}"
    if result[0] != "-":
        result = f"+{result}"
    return result


def parse_notice_time_or_interval(value):
    _, number, units = re.split("(\d+)", value)
    units = units_translation_dict[units]
    return {units: int(number)}


def apply_utc_offset(utc_offset, datetime_object, reverse=False):
    plus_or_minus = -1 if utc_offset[0] == "+" else 1
    if reverse:
        plus_or_minus *= -1
    offset_split = [int(x) for x in utc_offset[1:].split(":")]
    offset_h = offset_split[0]
    offset_min = 0
    if len(offset_split) > 1:
        offset_min = offset_split[1]
    utc_datetime = datetime_object + plus_or_minus * timedelta(
        hours=offset_h, minutes=offset_min
    )
    return utc_datetime


def get_utc_timestamp(local_date, local_time, utc_offset, notice_time):
    datetime_str = f"{local_date} {local_time}"
    datetime_object = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    utc_datetime = apply_utc_offset(utc_offset, datetime_object)
    if notice_time != "-":
        utc_datetime -= timedelta(**parse_notice_time_or_interval(notice_time))
    return int(utc_datetime.timestamp())


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    category = models.CharField(max_length=70, default="other")
    title = models.CharField(max_length=100)
    date = models.CharField(max_length=10, validators=[date_validator])
    time = models.CharField(max_length=5, default="", validators=[time_validator])
    notice_time = models.CharField(
        max_length=15, default="-", validators=[interval_and_notice_validator]
    )
    interval = models.CharField(
        max_length=15, default="-", validators=[interval_and_notice_validator]
    )
    info = models.TextField(max_length=3000, null=True, blank=True)
    utc_offset = models.CharField(
        max_length=6, default="", validators=[utc_offset_validator]
    )
    notification_type = models.CharField(
        max_length=10, default="", validators=[notification_type_validator]
    )
    utc_timestamp = models.IntegerField(editable=False)

    def save(self, *args, **kwargs):
        user_settings = UserSettings.objects.get(user=self.user)
        if not self.time:
            self.time = user_settings.default_time
        if not self.utc_offset:
            self.utc_offset = user_settings.default_utc_offset
        if not self.notification_type:
            self.notification_type = user_settings.default_notification_type
        if self.notification_type == "sms":
            if not self.user.phone_number:
                raise serializers.ValidationError(
                    "Phone number needs to be entered in settings in order to use the SMS notification type."
                )
        self.utc_timestamp = get_utc_timestamp(
            str(self.date), str(self.time), str(self.utc_offset), str(self.notice_time)
        )
        super(Event, self).save(*args, **kwargs)

    def __str__(self):
        return f"ID{self.pk}({self.user.pk})|{self.category} - {self.title}"


class Note(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    category = models.CharField(max_length=70, default="other")
    title = models.CharField(max_length=100, null=True, blank=True)
    info = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = (
                str(self.info)[:50] + "..."
                if len(str(self.info)) > 50
                else str(self.info)
            )
        super(Note, self).save(*args, **kwargs)

    def __str__(self):
        return f"ID{self.pk}({self.user.pk})|{self.category} - {self.title}"
