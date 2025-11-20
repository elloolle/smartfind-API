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
        end_period = instance.start_period + instance.delay
        data["end_period"] = str(end_period.isoformat())
        return data
