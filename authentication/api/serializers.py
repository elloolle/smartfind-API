from rest_framework import serializers
from subscription_payments.service import get_last_user_subscription
from ..models import User
from subscription_payments.api.serializers import SubscriptionSerializer


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"]
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        subscription = get_last_user_subscription(instance)
        data["subscription"] = SubscriptionSerializer(subscription).data
        del data["subscription"]["user"]
        return data
