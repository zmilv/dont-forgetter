from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.validators import (
    notification_type_validator,
    phone_number_validator,
    time_validator,
    utc_offset_validator,
)
from users.managers import CustomUserManager


class CustomUser(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    phone_number = models.CharField(
        max_length=15, null=True, blank=True, validators=[phone_number_validator]
    )
    premium_member = models.BooleanField(default=False)
    email_notifications_left = models.IntegerField(
        default=settings.NO_OF_FREE_EMAIL_NOTIFICATIONS
    )
    sms_notifications_left = models.IntegerField(
        default=settings.NO_OF_FREE_SMS_NOTIFICATIONS
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.is_staff:
            self.premium_member = True
        super(CustomUser, self).save(*args, **kwargs)


class UserSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    default_notification_type = models.CharField(
        max_length=10,
        default=settings.DEFAULT_NOTIFICATION_TYPE,
        validators=[notification_type_validator],
    )
    default_time = models.CharField(
        max_length=5, default=settings.DEFAULT_TIME, validators=[time_validator]
    )
    default_utc_offset = models.CharField(
        max_length=6,
        default=settings.DEFAULT_UTC_OFFSET,
        validators=[utc_offset_validator],
    )
    sms_sender_name = models.CharField(max_length=11, default="dont-forget")

    def __str__(self):
        return self.user.email
