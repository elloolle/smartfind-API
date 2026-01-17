from django.conf import settings
from django.db import models
from core.models import AbstractPayment, AbstractPaymentMethod


class Payment(AbstractPayment):
    income_amount = models.DecimalField(decimal_places=2, max_digits=20)


class PaymentMethod(AbstractPaymentMethod):
    pass
