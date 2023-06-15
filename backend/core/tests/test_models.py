from datetime import datetime, timezone

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from rest_framework.serializers import ValidationError

from core.models import (
    Event,
    apply_utc_offset,
    date_validator,
    get_utc_offset,
    get_utc_timestamp,
    interval_and_notice_validator,
    parse_notice_time_or_interval,
    time_validator,
    utc_offset_validator,
)
from users.models import CustomUser


class TestModelValidators(TestCase):
    """Test suite for model field validators"""

    def test_date_validator_valid(self):
        try:
            date_validator("2020-01-01")
        except ValidationError:
            self.fail("date_validator raised ValidationError unexpectedly!")

    def test_date_validator_invalid(self):
        with self.assertRaises(ValidationError):
            date_validator("2020/01/01")

    def test_time_validator_valid(self):
        try:
            time_validator("10:00")
        except ValidationError:
            self.fail("time_validator raised ValidationError unexpectedly!")

    def test_time_validator_invalid(self):
        with self.assertRaises(ValidationError):
            time_validator("10AM")

    def test_interval_and_notice_validator_valid(self):
        try:
            interval_and_notice_validator("15min")
        except ValidationError:
            self.fail(
                "interval_and_notice_validator raised ValidationError unexpectedly!"
            )

    def test_interval_and_notice_validator_invalid(self):
        with self.assertRaises(ValidationError):
            interval_and_notice_validator("15 minutes")

    def test_utc_offset_validator_valid(self):
        try:
            utc_offset_validator("+2")
        except ValidationError:
            self.fail("utc_offset_validator raised ValidationError unexpectedly!")

    def test_utc_offset_validator_invalid(self):
        with self.assertRaises(ValidationError):
            utc_offset_validator("2")


class TestModelHelperFuncs(TestCase):
    """Test suite for model helper functions"""

    def test_parse_notice_time_or_interval(self):
        result = parse_notice_time_or_interval("15min")
        expected_result = {"minutes": 15}
        self.assertEqual(result, expected_result)

    def test_apply_utc_offset(self):
        datetime_object = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        result = apply_utc_offset("+2", datetime_object)
        expected_result = datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc)
        self.assertEqual(result, expected_result)

    def test_get_utc_timestamp_without_notice(self):
        result = get_utc_timestamp("2024-01-01", "10:00", "+2", "-")
        expected_result = 1704096000  # Mon Jan 01 2024 08:00:00 GMT+0
        self.assertEqual(result, expected_result)

    def test_get_utc_timestamp_with_notice(self):
        result = get_utc_timestamp("2024-01-01", "10:00", "+2", "30min")
        expected_result = 1704094200  # Mon Jan 01 2024 07:30:00 GMT+0
        self.assertEqual(result, expected_result)


class TestEventModel(TestCase):
    """Test suite for Event model"""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="email@email.com", username="name", password=make_password("password")
        )

    def test_default_fields(self):
        default_fields = {
            "category": "other",
            "time": "10:00",
            "notice_time": "-",
            "interval": "-",
            "info": None,
        }
        dynamic_values = ["_state", "id", "utc_timestamp"]

        event_values = Event.objects.create(
            title="default", date="2020-01-01", user=self.user
        ).__dict__
        equivalent_event_values = Event.objects.create(
            title="default", date="2020-01-01", **default_fields, user=self.user
        ).__dict__
        for value in dynamic_values:
            del event_values[value]
            del equivalent_event_values[value]
        event_values = list(event_values.values())
        equivalent_event_values = list(equivalent_event_values.values())
        for i, attribute in enumerate(event_values):
            self.assertEqual(attribute, equivalent_event_values[i])
