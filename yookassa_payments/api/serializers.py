from django.contrib.auth import get_user_model
from rest_framework import serializers
from yookassa.domain.notification import WebhookNotification

from core.models import Subscription
from ..models import Payment, PaymentMethod

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

    def validate(self, attrs):
        event = attrs["event"]
        try:
            WebhookNotification(event)
        except Exception:
            raise serializers.ValidationError(event) from None
        attrs.update({"event_type": event["event"]})
        return attrs


class PaymentEventSerializer(serializers.Serializer):
    event = serializers.JSONField()

    def validate(self, attrs):
        event = attrs["event"]

        obj = event["object"]
        metadata = obj["metadata"]
        user_id = metadata.get("user_id")
        if not user_id:
            raise serializers.ValidationError("metadata.user_id is required")
        product_name = metadata.get("product")
        if not product_name:
            raise serializers.ValidationError("metadata.product is required")
        is_auto_pay = metadata.get("auto_pay", False)
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise serializers.ValidationError(f"User not found: {user_id}")

        sub = Subscription.objects.filter(user=user).first()

        attrs.update(
            {
                "user": user,
                "sub": sub,
                "obj": obj,
                "product_name": product_name,
                "is_auto_pay": is_auto_pay,
            }
        )
        return attrs
