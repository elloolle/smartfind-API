from django.conf import settings
from loguru import logger
import uuid
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from yookassa import Configuration, Payment
import json

Configuration.account_id = settings.YOOKASSA_ACCOUNT_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def make_payment(user_id, amount, metadata):
    payment = Payment.create(
        {
            "amount": {"value": amount, "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": settings.CHECKOUT_SUCCESS_URL,
            },
            "capture": True,
            "description": "",
            "save_payment_method": True,
            "metadata": metadata,
        },
        uuid.uuid4(),
    )
    return payment


def get_subscription_payment_link(payment):
    return payment.confirmation.confirmation_url


def get_subscription_payment(user_id, subscription_type):
    product = settings.PRODUCTS[subscription_type]
    metadata = {"user_id": user_id, "product": product}
    payment = make_payment(user_id, product.month_price, metadata)
    return payment


def make_auto_pay_every_30_days(payment_method_id, product):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=30,
        period=IntervalSchedule.DAYS,
    )
    PeriodicTask.objects.update_or_create(
        name="monthly_job_every_30_days",
        defaults={
            "interval": interval,
            "task": "yookassa_payments.tasks.withdraw_money_for_product",
            "enabled": True,
            "kwargs": json.dumps(
                {"payment_method_id": payment_method_id, product: product}
            ),
        },
    )


def decline_auto_pay_if_enable(payment_method_id):
    pass
