from rest_framework import serializers
from djstripe.models import Subscription
from django.contrib.auth import get_user_model
from ..service import get_last_user_subscription
from django.conf import settings
from loguru import logger

User = get_user_model()


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["id"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["status"] = instance.status
        subscription_product = instance.stripe_data["items"]["data"][0]
        product_name = subscription_product["price"]["lookup_key"]
        data["plan"] = settings.PRODUCTS[product_name]["plan"]
        data["expires_date"] = (
            instance.created + settings.PRODUCTS[product_name]["delay"]
        )
        return data


class SubscriptionProductNameSerializer(serializers.Serializer):
    product_name = serializers.CharField()

    def validate(self, data):
        request = self.context.get("request")
        user = request.user
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
