from django.conf import settings
from loguru import logger
from rest_framework import serializers
from ..models import Payment, PaymentMethod


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["status", "period_start", "amount"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["status", "details"]
