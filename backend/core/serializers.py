from django.conf import settings
from rest_framework import serializers

from core.models import Event, Note


class EventSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    notification_retries_left = serializers.HiddenField(
        default=settings.MAX_NOTIFICATION_RETRIES
    )

    class Meta:
        model = Event
        fields = "__all__"


class NoteSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Note
        fields = "__all__"
