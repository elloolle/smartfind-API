from django.db import models
from django.contrib.auth import get_user_model
from .utils import now

User = get_user_model()
from enum import Enum


class PaymentStatus(Enum):
    init = "init"
    pending = "pending"

    @classmethod
    def choices(cls):
        return [(member, member) for member in cls]


payment_statuses = ["init", "pending"]


class Payment(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=64)
    status = models.CharField(
        default=PaymentStatus.init, choices=PaymentStatus.choices()
    )

    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
