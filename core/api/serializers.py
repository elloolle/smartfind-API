from django.conf import settings
from loguru import logger
from rest_framework import serializers

from core.models import Subscription, SubscriptionStatus, Product
from django.utils.timezone import now


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = Subscription
        fields = ["id", "user", "status", "start_period", "product"]

    def create(self, validated_data):
        user = validated_data["user"]
        default_product = Product.objects.get(name=settings.DEFAULT_PRODUCT_NAME)
        return Subscription.objects.create(
            user=user,
            status=SubscriptionStatus.ACTIVE,
            start_period=now,
            product=default_product,
        )
