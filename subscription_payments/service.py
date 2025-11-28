from __future__ import annotations


import stripe

from django.conf import settings
from loguru import logger
from datetime import timedelta
from .helpers import now
from django.contrib.auth import get_user_model
from djstripe.models import Subscription, Customer

User = get_user_model()


def get_default_subscription_data():
    return {
        "status": "active",
        "plan": settings.PRODUCTS["default_subscription"]["plan"],
        "expires_date": "never",
    }


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
