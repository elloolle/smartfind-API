from django.conf import settings
from loguru import logger
from rest_framework import serializers
from ..models import Payment, PaymentMethod
from yookassa.domain.notification import WebhookNotification
from core.models import Subscription, PaymentMethodStatus
from django.contrib.auth import get_user_model

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["status", "period_start", "amount"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["status", "details"]


class EventTypeSerializer(serializers.Serializer):
    event = serializers.JSONField()

    def validate(self, data):
        event = data["event"]
        try:
            WebhookNotification(event)
        except Exception as e:
            raise serializers.ValidationError(e)
        data.update({"event_type": event["event"]})
        return data


class PaymentEventSerializer(serializers.Serializer):
    event = serializers.JSONField()

    def validate(self, attrs):
        event = attrs["event"]
        event_type = event.get("event")

        obj = event["object"]
        metadata = obj["metadata"]
        user_id = metadata.get("user_id")
        if not user_id:
            raise serializers.ValidationError("metadata.user_id is required")

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise serializers.ValidationError(f"User not found: {user_id}")

        sub = Subscription.objects.filter(user=user).first()
        event_status = event_type.removeprefix("payment.")

        attrs.update(
            {"user": user, "sub": sub, "event_status": event_status, "obj": obj}
        )
        return attrs
