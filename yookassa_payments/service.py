import json
import uuid
from dataclasses import dataclass, asdict

from django.conf import settings
from django_celery_beat.models import IntervalSchedule, PeriodicTask, ClockedSchedule
from loguru import logger
from yookassa import (
    Configuration,
    Payment as YookassaPayment,
    PaymentMethod as YookassaPaymentMethod,
)

from core.helpers import now
from core.models import Product, Subscription, PaymentMethodStatus
from core.service import create_default_subscription_to_user
from .models import PaymentMethod
from django.contrib.auth import get_user_model
from .helpers import make_anonymous_card

User = get_user_model()

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


def get_details_from_payment_method(payment_method):
    details = {"type": payment_method["type"]}
    if payment_method["type"] == "yoo_money":
        details["number"] = payment_method["account_number"]
    elif payment_method["type"] == "bank_card":
        card = payment_method["card"]
        details["number"] = make_anonymous_card(card["first6"], card["last4"])
        details["expire_date"] = f"{card["expiry_month"]}/{card["expiry_year"][2:4]}"
    else:
        logger.exception(f"yookassa payment method not supported: {payment_method}")
    return details


def log_payment_method_into_db(payment_method_json, user, status, with_details=True):
    if with_details:
        details = get_details_from_payment_method(payment_method_json)
    else:
        details = {}
    payment_method_obj, _ = PaymentMethod.objects.update_or_create(
        id=payment_method_json["id"],
        defaults={"user": user, "status": status, "details": details},
    )
    return payment_method_obj


def get_trial_subscription_payment_link(user_id, subscription_type):
    product = Product.objects.get(name=subscription_type)
    metadata = PaymentMetadata(user_id=user_id, product=product.name, trial=True)
    payment_method = make_payment_method(asdict(metadata))
    user = User.objects.get(id=user_id)
    log_payment_method_into_db(
        payment_method_json=dict(payment_method),
        user=user,
        status=PaymentMethodStatus.PENDING,
        with_details=False,
    )
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


def make_task_kwargs_and_name(payment_method, product, is_auto_pay):
    metadata = PaymentMetadata(
        user_id=payment_method.user.id,
        product=product.name,
        auto_pay=is_auto_pay,
    )
    task_kwargs = make_task_kwargs(
        payment_method.id, product.month_price, asdict(metadata)
    )
    if is_auto_pay:
        task_name = f"{AUTO_PAY_JOB_NAME}_{payment_method.id}"
    else:
        task_name = f"{PAY_ONCE_JOB_NAME}_{payment_method.id}"
    return task_kwargs, task_name


def make_auto_pay(payment_method, product):
    task_kwargs, task_name = make_task_kwargs_and_name(payment_method, product, True)
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=settings.DAYS_IN_MONTH,
        period=IntervalSchedule.DAYS,
    )
    PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            "interval": interval,
            "task": "yookassa_payments.tasks.withdraw_money",
            "start_time": now(),
            "enabled": True,
            "kwargs": task_kwargs,
        },
    )


def make_once_pay(payment_method, product):
    task_kwargs, task_name = make_task_kwargs_and_name(payment_method, product, False)
    clocked = ClockedSchedule.objects.create(clocked_time=now() + product.delay)
    PeriodicTask.objects.update_or_create(
        name=task_name,
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
