from rest_framework import serializers
from ..models import User
from core.api.serializers import SubscriptionSerializer


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    subscription = SubscriptionSerializer()

    class Meta:
        model = User
        fields = ["id", "username", "password", "subscription"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"]
        )
        SubscriptionSerializer().create({"user": user})
        return user
