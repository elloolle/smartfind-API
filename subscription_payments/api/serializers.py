from rest_framework import serializers
from djstripe.models import Subscription, PaymentMethod, Invoice
from django.contrib.auth import get_user_model
from ..service import get_last_user_subscription
from django.conf import settings
from loguru import logger
from datetime import datetime
from core.models import SubscriptionStatus

User = get_user_model()


class SubscriptionProductNameSerializer(serializers.Serializer):
    product_name = serializers.CharField()

    def validate(self, data):
        request = self.context.get("request")
        user = request.user
        subscription = getattr(user, "subscription", None)
        product_name = request.data.get("product_name")
        if (
            not settings.IGNORE_CLONE_SUBSCRIPTIONS
            and subscription
            and product_name == subscription.product.name
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
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ["djstripe_id", "status", "period_start", "amount"]
        ordering = ["period_start"]

    def get_status(self, obj):
        return obj.stripe_data["status"]

    def get_period_start(self, obj):
        period_start_unix = obj.stripe_data["period_start"]
        return datetime.utcfromtimestamp(period_start_unix)

    def get_amount(self, obj):
        amount = obj.stripe_data["amount_due"]
        return amount / 100
