from django.db import models
from django.contrib.auth import get_user_model
from .helpers import makeChoicesEnum

User = get_user_model()
from enum import Enum


@makeChoicesEnum(["init", "pending", "failed", "refunded", "succeeded"])
class PaymentStatus(Enum):
    pass


@makeChoicesEnum(
    [
        "incomplete",
        "incomplete_expired",
        "trialing",
        "active",
        "past_due",
        "canceled",
        "unpaid",
        "paused",
        "user_canceled",
        "user_did_not_pay",
    ]
)
class SubscriptionStatus(Enum):
    pass


class Payment(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=256)
    status = models.CharField(
        default=PaymentStatus.init, choices=PaymentStatus.choices()
    )
    amount = models.FloatField(null=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)


class Subscription(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(choices=SubscriptionStatus.choices())
    month_price = models.FloatField()
    start_period = models.DateTimeField()
    delay = models.DurationField()
    plan = models.CharField(max_length=64)
