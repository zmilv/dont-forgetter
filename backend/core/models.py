from django.db import models
from rest_framework import serializers
import re
from datetime import datetime, timedelta, timezone


DEFAULT_TIME = '10:00'

units_translation_dict = {
        'y': 'years',
        'm': 'months',
        'd': 'days',
        'h': 'hours',
        'min': 'minutes',
    }


def date_validator(value):
    regex = '^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$'  # yyyy-mm-dd
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError('Invalid date format. Valid format: yyyy-mm-hh')


def time_validator(value):
    regex = '^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$'  # hh:mm
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError('Invalid time format. Valid format: hh:mm')


def interval_and_notice_validator(value):
    regex = '^\d+(y|m|d|h|min)$'
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError('Invalid interval/notice format. Valid units: y, m, d, h, min. '
                                          'Valid examples: 15min, 1y')


def utc_offset_validator(value):
    regex = '^[+-]\d{1,2}:?\d{0,2}$'  # +/-h(:mm)
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError('Invalid UTC offset format. Valid examples: +1, -2:30')


def get_utc_offset(local_date):
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
    type = models.CharField(max_length=255, default='other')
    title = models.CharField(max_length=255)
    date = models.CharField(max_length=255, validators=[date_validator])
    time = models.CharField(max_length=255, default=DEFAULT_TIME, validators=[time_validator])
    notice_time = models.CharField(max_length=255, default='-', validators=[interval_and_notice_validator])
    interval = models.CharField(max_length=255, default='-', validators=[interval_and_notice_validator])
    info = models.TextField(max_length=3000, null=True, blank=True)
    utc_offset = models.CharField(max_length=255, default='', validators=[utc_offset_validator])
    utc_timestamp = models.IntegerField(editable=False)

    def save(self, *args, **kwargs):
        if not self.utc_offset:
            self.utc_offset = get_utc_offset(str(self.date))
        self.utc_timestamp = get_utc_timestamp(str(self.date), str(self.time), str(self.utc_offset),
                                               str(self.notice_time))
        super(Event, self).save(*args, **kwargs)

    def __str__(self):
        return f'ID{self.pk} - {self.title}({self.type})'
