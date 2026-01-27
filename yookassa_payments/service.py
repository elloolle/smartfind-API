from django.conf import settings
from loguru import logger
from django.forms.models import model_to_dict
import uuid
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from yookassa import Configuration, Payment, PaymentMethod
import json
from core.models import Product, SubscriptionStatus, Subscription
from datetime import timedelta
from core.helpers import now
from functools import partial

Configuration.account_id = settings.YOOKASSA_ACCOUNT_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

PAYMENT_JOB_NAME = "yookassa_payment_job"


def make_payment(amount, metadata):
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


def make_payment_method(metadata):
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
    payment = make_payment(product.month_price, metadata)
    return payment.confirmation.confirmation_url


def get_trial_subscription_payment_link(user_id, subscription_type):
    product = Product.objects.get(name=subscription_type)
    metadata = {
        "user_id": user_id,
        "product": product.name,
        "trial": True,
    }
    payment_method = make_payment_method(metadata)
    return payment_method.confirmation.confirmation_url


def make_auto_pay_every_n_days_after_k_days(payment_method, product, n, k):
    metadata = {"user_id": payment_method.user.id, "auto_pay": True}
    task_kwargs = json.dumps(
        {
            "payment_method_id": payment_method.id,
            "amount": product.month_price,
            "metadata": metadata,
        },
        sort_keys=True,
    )
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=n,
        period=IntervalSchedule.DAYS,
    )
    PeriodicTask.objects.update_or_create(
        name=f"{PAYMENT_JOB_NAME}_{payment_method.id}",
        defaults={
            "interval": interval,
            "task": "yookassa_payments.tasks.withdraw_money",
            "start_time": now() + timedelta(days=k),
            "enabled": True,
            "kwargs": task_kwargs,
        },
    )


make_auto_pay = partial(
    make_auto_pay_every_n_days_after_k_days, n=settings.DAYS_IN_MONTH, k=0
)

make_trial_auto_pay = partial(
    make_auto_pay_every_n_days_after_k_days,
    n=settings.DAYS_IN_MONTH,
    k=settings.TRIAL_PERIOD_DAYS,
)


def decline_auto_pay(payment_method_id):
    PeriodicTask.objects.filter(
        name=f"{PAYMENT_JOB_NAME}_{payment_method_id}",
    ).delete()


def decline_subscription(subscription):
    subscription.status = SubscriptionStatus.UNPAID
    subscription.save()
    decline_auto_pay(subscription.id)


def decline_subscription_by_user(user):
    subscription = Subscription.objects.get(user=user)
    decline_subscription(subscription)
