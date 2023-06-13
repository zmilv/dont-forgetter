import re

from rest_framework import serializers

units_translation_dict = {
    "y": "years",
    "m": "months",
    "d": "days",
    "h": "hours",
    "min": "minutes",
}


def date_validator(value):
    regex = "^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$"  # yyyy-mm-dd
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError(
            "Invalid date format. Valid format: yyyy-mm-hh"
        )


def time_validator(value):
    regex = "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$"  # hh:mm
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError("Invalid time format. Valid format: hh:mm")


def interval_and_notice_validator(value):
    regex = "^\d+(y|m|d|h|min)$"
    if not re.fullmatch(regex, value) and value != "-":
        raise serializers.ValidationError(
            "Invalid interval/notice format. Valid units: y, m, d, h, min. "
            "Valid examples: 15min, 1y"
        )


def utc_offset_validator(value):
    regex = "^[+-]\d{1,2}:?\d{0,2}$"  # +/-h(:mm)
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError(
            "Invalid UTC offset format. Valid examples: +1, -2:30"
        )


def notification_type_validator(value):
    if value not in ("email", "sms"):
        raise serializers.ValidationError(
            'Invalid notification type. Currently available choices: email, sms'
        )
