from datetime import datetime, timezone

from django.test import TestCase
from rest_framework.serializers import ValidationError

from core.models import (
    Event,
    apply_utc_offset,
    custom_variables_validator,
    date_validator,
    get_utc_timestamp,
    interval_and_notice_validator,
    parse_notice_time_or_interval,
    time_validator,
    utc_offset_validator,
)


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

    def test_custom_variables_validator_valid(self):
        try:
            custom_variables_validator("name=Tom")
        except ValidationError:
            self.fail("custom_variables_validator raised ValidationError unexpectedly!")

    def test_custom_variables_validator_valid_two_variables(self):
        try:
            custom_variables_validator("name=Tom; var2=variable2")
        except ValidationError:
            self.fail("custom_variables_validator raised ValidationError unexpectedly!")

    def test_custom_variables_validator_invalid(self):
        with self.assertRaises(ValidationError):
            custom_variables_validator("name-Tom")


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
