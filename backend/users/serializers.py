from django.contrib.auth import authenticate
from rest_framework import serializers

from users.models import CustomUser, UserSettings


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer class to serialize CustomUser model.
    """

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "email",
            "phone_number",
            "email_notifications_left",
            "sms_notifications_left",
            "premium_member",
        )


class CustomUserUpdateSerializer(serializers.ModelSerializer):
    class Meta(CustomUserSerializer.Meta):
        read_only_fields = (
            "email_notifications_left",
            "sms_notifications_left",
            "premium_member",
        )


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer class to serialize registration requests and create a new user.
    """

    class Meta:
        model = CustomUser
        fields = ("id", "username", "email", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer class to authenticate users with email and password.
    """

    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect Credentials")


class UserSettingsSerializer(CustomUserSerializer):
    """
    Serializer class to serialize the UserSettings model
    """

    class Meta:
        model = UserSettings
        fields = (
            "default_notification_type",
            "default_time",
            "default_utc_offset",
        )
