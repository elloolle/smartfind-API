from __future__ import annotations

import os

from dotenv import load_dotenv
import stripe

from .models import Subscription, PaymentStatus
from django.conf import settings
from loguru import logger
from datetime import timedelta
from .helpers import now
from django.contrib.auth import get_user_model

User = get_user_model()
load_dotenv()
stripe.api_key = os.getenv("TEST_STRIPE_API_KEY")


def get_event(request):
    try:
        signature = request.headers.get("stripe-signature")
        event = stripe.Webhook.construct_event(
            payload=request.body,
            sig_header=signature,
            secret=os.getenv("TEST_STRIPE_WEBHOOK_KEY"),
        )
        return event
    except Exception as e:
        if not settings.DEBUG:
            raise "error in webhook signature"


def update_user_subscription(id, user, subscription_status, product_name):
    product = settings.PRODUCTS[product_name]
    Subscription.objects.update_or_create(
        id=id,
        defaults={
            "user": user,
            "status": subscription_status,
            "month_price": product["month_price"],
            "start_period": now(),
            "delay": product["delay"],
            "plan": product["plan"],
        },
    )


def get_last_user_subscription(user):
    subscriptions = Subscription.objects.filter(user=user).order_by("-start_period")
    if subscriptions.count() == 0:
        return None

    return subscriptions.first()


def get_payment_status(status):
    if status in ["failed", "disputed", "uncollectible", "canceled", "void", "deleted"]:
        return PaymentStatus.failed

    elif status in ["refunded", "partially_refunded"]:
        return PaymentStatus.refunded

    elif status in ["succeeded", "paid"]:
        return PaymentStatus.succeeded

    elif status in [
        "pending",
        "draft",
        "open",
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "incomplete_expired",
    ]:
        return PaymentStatus.pending

    else:
        logger.error("Unknown payment status: {}".format(status))
        return PaymentStatus.other
