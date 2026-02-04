import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.forms.models import model_to_dict

from .helpers import now

User = get_user_model()


class Product(models.Model):
    name = models.CharField(max_length=256, unique=True, primary_key=True)
    plan = models.CharField(max_length=64)
    delay = models.DurationField(null=True)
    month_price = models.FloatField()

    def to_dict(self):
        model_dict = model_to_dict(self)
        model_dict["delay"] = str(model_dict["delay"])
        return model_dict


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    UNPAID = "unpaid", "Unpaid"


def now_plus_one_month():
    return now() + timedelta(days=settings.DAYS_IN_MONTH)


class Subscription(models.Model):
    id = models.CharField(max_length=256, default=uuid.uuid4, primary_key=True)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, related_name="subscription", null=True
    )
    status = models.CharField(choices=SubscriptionStatus.choices)
    start_period = models.DateTimeField(default=now)
    end_period = models.DateTimeField(default=now_plus_one_month, null=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )

    @property
    def product_name(self):
        return self.product.name

    @property
    def is_trial(self):
        return self.product_name == settings.TRIAL_PRODUCT_NAME


class PaymentStatus(models.TextChoices):
    PAID = "paid", "Paid"
    UNPAID = "unpaid", "Unpaid"


class AbstractPayment(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment")
    status = models.CharField(choices=PaymentStatus.choices)
    period_start = models.DateTimeField(default=now)
    amount = models.DecimalField(decimal_places=2, max_digits=10)

    class Meta:
        abstract = True


class PaymentMethodStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CANCELED = "canceled", "Canceled"
    PENDING = "pending", "Pending"


class AbstractPaymentMethod(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_method"
    )
    status = models.CharField(choices=PaymentMethodStatus.choices)
    details = models.JSONField(default=dict)

    class Meta:
        abstract = True
