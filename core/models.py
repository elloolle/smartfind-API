import uuid

from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    UNPAID = "unpaid", "Unpaid"
    PAUSED = (
        "paused",
        "Paused",
    )  # если триал версия закончилась, а пользователь не оплатил


class Product(models.Model):
    name = models.CharField(max_length=256, unique=True, primary_key=True)
    plan = models.CharField(max_length=64)
    delay = models.DurationField(null=True)
    month_price = models.FloatField()


class Subscription(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, related_name="subscription", null=True
    )
    status = models.CharField(choices=SubscriptionStatus.choices)
    start_period = models.DateTimeField()
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )
