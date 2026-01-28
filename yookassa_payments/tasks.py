from celery import shared_task
from yookassa import Payment
from core.models import Subscription, SubscriptionStatus
from core.helpers import now


@shared_task
def withdraw_money(payment_method_id, amount, metadata):
    payment = Payment.create(
        {
            "amount": {"value": amount, "currency": "RUB"},
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": "Заказ",
            "metadata": metadata,
        }
    )
    return payment.json()


@shared_task
def update_subscriptions_statuses_based_on_end_period():
    Subscription.objects.filter(end_period__lte=now()).update(
        status=SubscriptionStatus.UNPAID
    )
