from django.db import models

from bitapi.utils import now


class StripeSubscription(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    status = models.CharField(max_length=64, default="init")
    price = models.CharField(max_length=64)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    date_created = models.DateTimeField(default=now, db_index=True)
    date_updated = models.DateTimeField(auto_now=True)
    current_period_end = models.DateTimeField()
    current_period_start = models.DateTimeField()
    canceled = models.BooleanField(default=False)
    data = models.JSONField(null=True)
    auto_pay = models.JSONField(null=True)


class StripePayment(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    type = models.CharField(max_length=64)
    status = models.CharField(max_length=64, default="init")
    date_created = models.DateTimeField(default=now, db_index=True)
    data = models.JSONField(null=True)
