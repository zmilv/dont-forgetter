from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.validators import time_validator, utc_offset_validator, notification_type_validator, phone_number_validator
from users.managers import CustomUserManager


class CustomUser(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class UserSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, null=True, blank=True, validators=[phone_number_validator])
    default_notification_type = models.CharField(
        max_length=10, default="email", validators=[notification_type_validator]
    )
    default_time = models.CharField(
        max_length=5, default="10:00", validators=[time_validator]
    )
    default_utc_offset = models.CharField(
        max_length=6, default="+0", validators=[utc_offset_validator]
    )

    def __str__(self):
        return self.user.email
