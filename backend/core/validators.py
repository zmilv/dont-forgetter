import re

from rest_framework import serializers

regex_dict = {
    "date": "^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$",  # yyyy-mm-dd
    "time": "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$",  # hh:mm
    "interval_and_notice": "^\d+(y|m|d|h|min)$",
    "utc_offset": "^[+-]\d{1,2}:?\d{0,2}$",  # +/-h(:mm)
    "phone_number": "^370\d{8}$",
    "email": "^[a-z0-9]+(?:[._][a-z0-9]+)*@(?:\w+\.)+\w{2,3}$",
    "custom_variables": "(\w+(?:\d+)?)=([^;]+)(?:;|$)"
}

units_translation_dict = {
    "y": "years",
    "m": "months",
    "d": "days",
    "h": "hours",
    "min": "minutes",
}


def date_validator(value):
    regex = regex_dict["date"]
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError(
            "Invalid date format. Valid format: yyyy-mm-hh"
        )


def time_validator(value):
    regex = regex_dict["time"]
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError("Invalid time format. Valid format: hh:mm")


def interval_and_notice_validator(value):
    regex = regex_dict["interval_and_notice"]
    if not re.fullmatch(regex, value) and value != "-":
        raise serializers.ValidationError(
            "Invalid interval/notice format. Valid units: y, m, d, h, min. "
            "Valid examples: 15min, 1y"
        )


def utc_offset_validator(value):
    regex = regex_dict["utc_offset"]
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError(
            "Invalid UTC offset format. Valid examples: +1, -2:30"
        )


def notification_type_validator(value):
    if value not in ("email", "sms"):
        raise serializers.ValidationError(
            "Invalid notification type. Currently available choices: email, sms"
        )


def phone_number_validator(value):
    regex = regex_dict["phone_number"]
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError(
            "Invalid phone number. Currently only Lithuanian numbers are accepted. Number has to start with 370 and"
            " consist of 11 digits in total."
        )


def email_validator(value):
    regex = regex_dict["email"]
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError("Invalid email format.")


def count_validator(value):
    if value < 2:
        raise serializers.ValidationError("Count must be at least 2 if an interval is set")


def custom_variables_validator(value):
    regex = regex_dict["custom_variables"]
    if not re.fullmatch(regex, value):
        raise serializers.ValidationError("Invalid custom variables format. Valid example: 'name=Tom; surname=Smith'")
