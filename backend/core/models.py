from django.db import models
from rest_framework import serializers
import re
import time

DEFAULT_TIME = '10:00'


def date_validator(value):
    regex = '^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$'  # yyyy-mm-dd
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError('Invalid date format. Valid format: yyyy-mm-hh')


def time_validator(value):
    regex = '^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$'  # hh:mm
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError('Invalid time format. Valid format: hh:mm')


def get_local_timezone():
    return time.tzname[time.daylight]


class Event(models.Model):
    type = models.CharField(max_length=255, default='other')
    title = models.CharField(max_length=255)
    date = models.CharField(max_length=255, validators=[date_validator])
    time = models.CharField(max_length=255, default=DEFAULT_TIME, validators=[time_validator])
    timezone = models.CharField(max_length=255, default=get_local_timezone())
    interval = models.CharField(max_length=255, default='once')
    info = models.TextField(max_length=3000, null=True, blank=True)

    def __str__(self):
        return f'{self.type} - {self.title}'
