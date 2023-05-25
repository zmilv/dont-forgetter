from django.db import models
from django.conf import settings
from core.validators import units_translation_dict, date_validator, time_validator, interval_and_notice_validator,\
    utc_offset_validator
from users.models import UserSettings
from django_cryptography.fields import encrypt
from datetime import datetime, timedelta, timezone
import re


def get_utc_offset(local_date):  # Unused. Todo: derive from user location setting
    datetime_object = datetime.strptime(local_date, '%Y-%m-%d')
    local_timezone = datetime_object.astimezone()
    offset = local_timezone.utcoffset() // timedelta(minutes=1) / 60
    hours = int(offset)
    mins = int(offset % 1 * 60)
    if mins:
        result = f'{hours}:{mins}'
    else:
        result = f'{hours}'
    if result[0] != '-':
        result = f'+{result}'
    return result


def parse_notice_time_or_interval(value):
    _, number, units = re.split('(\d+)', value)
    units = units_translation_dict[units]
    return {units: int(number)}


def apply_utc_offset(utc_offset, datetime_object):
    plus_or_minus = -1 if utc_offset[0] == '+' else 1
    offset_split = [int(x) for x in utc_offset[1:].split(':')]
    offset_h = offset_split[0]
    offset_min = 0
    if len(offset_split) > 1:
        offset_min = offset_split[1]
    utc_datetime = datetime_object + plus_or_minus * timedelta(hours=offset_h, minutes=offset_min)
    return utc_datetime.replace(tzinfo=timezone.utc)


def get_utc_timestamp(local_date, local_time, utc_offset, notice_time):
    datetime_str = f'{local_date} {local_time}'
    datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
    utc_datetime = apply_utc_offset(utc_offset, datetime_object)
    if notice_time != '-':
        utc_datetime -= timedelta(**parse_notice_time_or_interval(notice_time))
    return int(utc_datetime.timestamp())


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    type = encrypt(models.CharField(max_length=70, default='other'))
    title = encrypt(models.CharField(max_length=100))
    date = models.CharField(max_length=10, validators=[date_validator])
    time = models.CharField(max_length=5, default='', validators=[time_validator])
    notice_time = models.CharField(max_length=15, default='-', validators=[interval_and_notice_validator])
    interval = models.CharField(max_length=15, default='-', validators=[interval_and_notice_validator])
    info = encrypt(models.TextField(max_length=3000, null=True, blank=True))
    utc_offset = models.CharField(max_length=6, default='', validators=[utc_offset_validator])
    utc_timestamp = models.IntegerField(editable=False)

    def save(self, *args, **kwargs):
        user_settings = UserSettings.objects.get(user=self.user)
        if not self.time:
            self.time = user_settings.default_time
        if not self.utc_offset:
            self.utc_offset = user_settings.default_utc_offset
        self.utc_timestamp = get_utc_timestamp(str(self.date), str(self.time), str(self.utc_offset),
                                               str(self.notice_time))
        super(Event, self).save(*args, **kwargs)

    def __str__(self):
        return f'ID{self.pk}({self.user.pk})|{self.type} - {self.title}'


class Note(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    type = encrypt(models.CharField(max_length=255, default='other'))
    title = encrypt(models.CharField(max_length=255, null=True, blank=True))
    info = encrypt(models.TextField(max_length=3000))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = str(self.info)[:50] + '...' if len(str(self.info)) > 50 else str(self.info)[:50]
        super(Note, self).save(*args, **kwargs)

    def __str__(self):
        return f'ID{self.pk}({self.user.pk})|{self.type} - {self.title}'
