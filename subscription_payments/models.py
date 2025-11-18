from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from enum import Enum


class PaymentStatus(Enum):
    init = "init"
    pending = "pending"

    @classmethod
    def choices(cls):
        return [(member, member) for member in cls]


class SubscriptionStatus(Enum):
    active = "active"
    user_canceled = "user_canceled"
    user_did_not_pay = "user_did_not_pay"

    @classmethod
    def choices(cls):
        return [(member, member) for member in cls]


class Payment(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=64)
    status = models.CharField(
        default=PaymentStatus.init, choices=PaymentStatus.choices()
    )
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)


class Subscription(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(choices=SubscriptionStatus.choices())
    month_price = models.FloatField()
    start_period = models.DateTimeField()
    delay = models.DurationField()
