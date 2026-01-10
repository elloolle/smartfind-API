from __future__ import annotations


import stripe

from django.conf import settings
from loguru import logger
from django.contrib.auth import get_user_model
from djstripe.models import Subscription, Customer
from core.models import SubscriptionStatus, Product
from core.models import Subscription as CoreSubscription

User = get_user_model()


def get_last_user_subscription(user):
    try:
        customer = Customer.objects.get(id=user.customer_id)
    except Customer.DoesNotExist:
        return None
    subscriptions = Subscription.objects.filter(customer=customer)
    if not subscriptions:
        return None
    return subscriptions.order_by("-created").first()


def log_webhooks(request):
    if not settings.IS_WEBHOOK_LOGGING_ON:
        return
    logs_path = settings.WEBHOOKS_LOGS_PATH
    event_name = settings.WEBHOOKS_EVENT_NAME_TO_LOG

    event = get_event(request)
    if event["type"] != event_name:
        return
    event_dict = event.to_dict_recursive()
    logger.add(
        settings.WEBHOOKS_LOGS_PATH,
        format="{message}",  # <-- никаких INFO, времени, уровня — только сообщение!
        level="TRACE",  # позволяет логировать .log(...)
    )
    logger.log("TRACE", f"{event_dict!r},")


def get_core_sub_from_djstripe_sub(djstripe_sub):
    id = djstripe_sub.id
    product_name = djstripe_sub.stripe_data["items"]["data"][0]["price"]["lookup_key"]
    user = User.objects.get(customer_id=djstripe_sub.customer.id)
    djstripe_sub_status = djstripe_sub.status
    STRIPE_TO_CORE_STATUS = {
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.ACTIVE,
        "paused": SubscriptionStatus.PAUSED,
        "past_due": SubscriptionStatus.UNPAID,
        "canceled": SubscriptionStatus.UNPAID,
        "unpaid": SubscriptionStatus.UNPAID,
        "incomplete": SubscriptionStatus.UNPAID,
        "incomplete_expired": SubscriptionStatus.UNPAID,
    }
    status = STRIPE_TO_CORE_STATUS.get(djstripe_sub_status, SubscriptionStatus.UNPAID)
    start_period = djstripe_sub.created
    product = Product.objects.get(name=product_name)
    return CoreSubscription.objects.create(
        id=id, user=user, status=status, start_period=start_period, product=product
    )
