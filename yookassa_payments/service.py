from django.conf import settings
from loguru import logger
from django.forms.models import model_to_dict
import uuid
from django_celery_beat.models import IntervalSchedule, PeriodicTask, ClockedSchedule
from yookassa import (
    Configuration,
    Payment as YookassaPayment,
    PaymentMethod as YookassaPaymentMethod,
)
import json
from .models import PaymentMethod
from core.models import Product, SubscriptionStatus, Subscription, PaymentMethodStatus
from datetime import timedelta
from core.helpers import now
from functools import partial
from core.service import create_default_subscription_to_user
from dataclasses import dataclass, asdict

Configuration.account_id = settings.YOOKASSA_ACCOUNT_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

AUTO_PAY_JOB_NAME = "yookassa_auto_pay_job"
PAY_ONCE_JOB_NAME = "yookassa_pay_once_job"


@dataclass
class PaymentMetadata:
    user_id: str
    product: str
    auto_pay: bool = False
    trial: bool = False


def make_payment(amount, metadata):
    payment = YookassaPayment.create(
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
    payment_method = YookassaPaymentMethod.create(
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
    metadata = PaymentMetadata(user_id=user_id, product=product.name)
    payment = make_payment(product.month_price, asdict(metadata))
    return payment.confirmation.confirmation_url


def get_trial_subscription_payment_link(user_id, subscription_type):
    product = Product.objects.get(name=subscription_type)
    metadata = PaymentMetadata(user_id=user_id, product=product.name, trial=True)
    payment_method = make_payment_method(asdict(metadata))
    return payment_method.confirmation.confirmation_url


def make_task_kwargs(payment_method_id, amount, metadata):
    return json.dumps(
        {
            "payment_method_id": payment_method_id,
            "amount": amount,
            "metadata": metadata,
        },
        sort_keys=True,
    )


def make_auto_pay_every_n_days_after_k_days(payment_method, product, n, k):
    metadata = PaymentMetadata(
        user_id=payment_method.user.id, product=product.name, auto_pay=True
    )
    task_kwargs = make_task_kwargs(
        payment_method.id, product.month_price, asdict(metadata)
    )
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=n,
        period=IntervalSchedule.DAYS,
    )
    PeriodicTask.objects.update_or_create(
        name=f"{AUTO_PAY_JOB_NAME}_{payment_method.id}",
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


def make_once_pay(payment_method, product):
    metadata = PaymentMetadata(user_id=payment_method.user.id, product=product.name)
    task_kwargs = make_task_kwargs(
        payment_method.id, product.month_price, asdict(metadata)
    )
    clocked = ClockedSchedule.objects.create(clocked_time=now() + product.delay)
    PeriodicTask.objects.update_or_create(
        name=f"{PAY_ONCE_JOB_NAME}_{payment_method.id}",
        defaults={
            "clocked": clocked,
            "one_off": True,
            "enabled": True,
            "kwargs": task_kwargs,
            "task": "yookassa_payments.tasks.withdraw_money",
        },
    )


def decline_auto_pay(payment_method_id):
    PeriodicTask.objects.filter(
        name=f"{AUTO_PAY_JOB_NAME}_{payment_method_id}",
    ).delete()


def delete_subscription_and_autopay(subscription):
    user = subscription.user
    payment_method_id = PaymentMethod.objects.filter(
        user=user, status=PaymentMethodStatus.ACTIVE
    ).id
    decline_auto_pay(payment_method_id)
    subscription.delete()
    create_default_subscription_to_user(user)


def delete_subscription_and_autopay_by_user(user):
    subscription = Subscription.objects.get(user=user)
    delete_subscription_and_autopay(subscription)
