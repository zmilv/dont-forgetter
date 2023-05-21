from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import UserSettings

User = get_user_model()


@receiver(post_save, sender=User)
def create_usersettings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_usersettings(sender, instance, **kwargs):
    instance.usersettings.save()
