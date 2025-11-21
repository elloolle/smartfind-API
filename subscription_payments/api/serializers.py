from rest_framework import serializers

from ..models import Payment, Subscription


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["type", "amount"]


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id",
            "user",
            "status",
            "month_price",
            "start_period",
            "delay",
            "plan",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        end_period = None
        if instance.delay:
            end_period = instance.start_period + instance.delay
            end_period = str(end_period.isoformat())
        data["end_period"] = end_period
        return data


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id"]
