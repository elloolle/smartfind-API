from rest_framework import serializers
from djstripe.models import Subscription, PaymentMethod, Invoice
from django.contrib.auth import get_user_model
from ..service import get_last_user_subscription
from django.conf import settings
from loguru import logger
from datetime import datetime


User = get_user_model()


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()
    expires_date = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ["id", "status", "plan", "expires_date"]

    def get_product_name(self, instance):
        try:
            return instance.stripe_data["items"]["data"][0]["price"]["lookup_key"]
        except (KeyError, IndexError, TypeError):
            return None

    def get_plan(self, instance):
        product_name = self.get_product_name(instance)
        if not product_name:
            return None
        return settings.PRODUCTS[product_name]["plan"]

    def get_expires_date(self, instance):
        product_name = self.get_product_name(instance)
        if not product_name:
            return None
        return instance.created + settings.PRODUCTS[product_name]["delay"]


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


class CheckSubscriptionExistsSerializer(serializers.Serializer):
    subscription_id = serializers.CharField(read_only=True)

    def validate(self, data):
        request = self.context.get("request")
        subscription = get_last_user_subscription(request.user)
        if not subscription:
            raise serializers.ValidationError(
                detail="user can't delete default subscription"
            )
        self.subscription_id = subscription.id
        data["subscription_id"] = subscription.id
        return data


class PaymentMethodSerializer(serializers.ModelSerializer):
    card_number = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = ["djstripe_id", "card_number"]

    def get_card_number(self, obj):
        last4 = obj.stripe_data.get("card", {}).get("last4")
        if not last4:
            return "**** **** **** ****"
        return "**** **** **** " + last4


class InvoiceSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    period_start = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ["djstripe_id", "status", "period_start", "amount_due"]
        ordering = ["period_start"]

    def get_status(self, obj):
        return obj.stripe_data["status"]

    def get_period_start(self, obj):
        period_start_unix = obj.stripe_data["period_start"]
        return datetime.utcfromtimestamp(period_start_unix)

    def get_amount_due(self, obj):
        amount_due = obj.stripe_data["amount_due"]
        return amount_due / 100
