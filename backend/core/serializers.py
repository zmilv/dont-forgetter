from core.models import Event
from rest_framework import serializers


class EventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
