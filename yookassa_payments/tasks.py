from celery import shared_task
from core.models import Subscription, SubscriptionStatus
from core.helpers import now
from core.service import create_default_subscription_to_user
from .service import withdraw_money as withdraw_money_service


@shared_task
def withdraw_money(payment_method_id, amount, metadata):
    return withdraw_money_service(payment_method_id, amount, metadata)


@shared_task
def update_subscriptions_statuses_based_on_end_period():
    subscriptions = Subscription.objects.filter(end_period__lte=now())
    for subscription in subscriptions:
        user = subscription.user
        subscription.delete()
        create_default_subscription_to_user(user)
