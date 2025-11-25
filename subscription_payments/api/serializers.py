from rest_framework import serializers
from djstripe.models import Subscription
from django.contrib.auth import get_user_model
from ..service import get_last_user_subscription
from django.conf import settings

User = get_user_model()


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["__all__"]


class SubscriptionProductNameSerializer(serializers.Serializer):
    product_name = serializers.CharField()

    def validate(self, data):
        user = self.context["request"].user
        subscription = get_last_user_subscription(user)
        product_name = request.data.get("product_name")
        if (
            not settings.IGNORE_CLONE_SUBSCRIPTIONS
            and subscription
            and product_name == subscription.plan
        ):
            raise serializers.ValidationError("User already subscribed for this plan")
        data["product_name"] = product_name
        return data
