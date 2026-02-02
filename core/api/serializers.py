import uuid

from django.conf import settings
from loguru import logger
from rest_framework import serializers

from core.models import Subscription, SubscriptionStatus, Product
from ..service import create_default_subscription_to_user


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = Subscription
        fields = ["id", "user", "status", "start_period", "product", "end_period"]
