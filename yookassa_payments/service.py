from django.conf import settings
from loguru import logger
from django.forms.models import model_to_dict
import uuid
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from yookassa import Configuration, Payment, PaymentMethod
import json
from core.models import Product
from datetime import timedelta
from core.helpers import now

Configuration.account_id = settings.YOOKASSA_ACCOUNT_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

PAYMENT_JOB_NAME = "yookassa_payment_job"


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


def make_payment_method(user_id, metadata):
    payment_method = PaymentMethod.create(
        {
            "confirmation": {
                "type": "redirect",
                "return_url": settings.CHECKOUT_SUCCESS_URL,
            },
            "type": "bank_card",
            "metadata": metadata,
        }
    )
    return payment_method


def get_subscription_payment_link(user_id, subscription_type):
    product = Product.objects.get(name=subscription_type)
    metadata = {"user_id": user_id, "product": product.name}
    payment = make_payment(user_id, product.month_price, metadata)
    return payment.confirmation.confirmation_url


def get_trial_subscription_payment_link(user_id, subscription_type):
    product = Product.objects.get(name=subscription_type)
    metadata = {
        "user_id": user_id,
        "product": product.name,
        "trial": True,
    }
    payment_method = make_payment_method(user_id, metadata)
    return payment_method.confirmation.confirmation_url


def make_auto_pay_every_n_days_after_k_days(payment_method_id, product, n, k):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=n,
        period=IntervalSchedule.DAYS,
    )
    task_kwargs = json.dumps(
        {"payment_method_id": payment_method_id, "product_id": product.pk},
        sort_keys=True,
    )
    PeriodicTask.objects.update_or_create(
        name=f"{PAYMENT_JOB_NAME}_{payment_method_id}",
        defaults={
            "interval": interval,
            "task": "yookassa_payments.tasks.withdraw_money_for_product",
            "start_time": now() + timedelta(days=k),
            "enabled": True,
            "kwargs": task_kwargs,
        },
    )


def make_auto_pay(payment_method_id, product):
    make_auto_pay_every_n_days_after_k_days(
        payment_method_id, product, settings.DAYS_IN_MONTH, 0
    )


def make_trial_auto_pay(payment_method_id, product):
    make_auto_pay_every_n_days_after_k_days(
        payment_method_id, product, settings.DAYS_IN_MONTH, settings.TRIAL_PERIOD_DAYS
    )


def decline_auto_pay(payment_method_id):
    PeriodicTask.objects.filter(
        name=f"{PAYMENT_JOB_NAME}_{payment_method_id}",
    ).delete()
