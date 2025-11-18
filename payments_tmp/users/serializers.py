from datetime import timedelta, timezone
import django
from django.contrib.auth import get_user_model
from rest_framework import serializers
from bitapi.users.models import Questionnaire, SocialMediaSubscribeRequest

from bitapi.users.models import User as UserType
from bitapi.utils import get_subscription_options, add_values

User = get_user_model()


class UserSerializer(serializers.ModelSerializer[UserType]):
    subscription_period = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "username",
            "name",
            "popup",
            "used_words_simple_scan",
            "subscription",
            "id",
            "enrolled",
            "onboarding_completed",
            "premium_or_custom_available_until",
            "subscription_period"
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        limits = get_subscription_options(instance.subscription_name())
        if instance.subscription_name() == "Pay as you go":
            limits.update(instance.additional_limits or {})
        else:
            limits = add_values(limits, instance.additional_limits or {})
        ret.update(limits)
        for k, v in (instance.additional_limits or {}).items():
            ret["additional_" + k] = v
        ret["used_words_simple_scan"] = min(
            ret["granted_words_simple_scan"], ret["used_words_simple_scan"]
        )
        return ret

    def get_subscription(self, obj):
        user = User.objects.get(username=obj.username)
        print(user.subscription_name())
        return user.subscription_name()

    def get_subscription_period(self, obj):
        sub = User.objects.get(username=obj.username).get_subscription()
        if not sub:
            return None
        return "monthly" if "monthly" in sub.price else "yearly"


class SignUpSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    source = serializers.CharField()


class QuestionnaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questionnaire
        fields = ["work_place", "company_name", "job_title", "job_position", "ai_detector_purpose", "current_solution", "discovery_source", "other_tools", "important_features"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        user = self.context["request"].user
        questionnaire = Questionnaire.objects.create(user=user, **validated_data)
        return questionnaire

class SocialMediaSubscribeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaSubscribeRequest
        fields = ["source", "link_url"]

    def create(self, validated_data):
        user = self.context["request"].user
        return SocialMediaSubscribeRequest.objects.create(user=user, **validated_data)
