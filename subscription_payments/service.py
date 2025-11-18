from __future__ import annotations

import os
from typing import TypedDict

from dotenv import load_dotenv
import stripe
from .models import Subscription, SubscriptionStatus
from django.conf import settings

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


def give_product_to_user(user, product_name):
    if product_name == "pro_month_subscription":
        delay = "month"
        Subscription.objects.create(
            user=user,
            status=SubscriptionStatus.active,
            month_price=settings.SUBSCRIPTION_MONTH_PRICE["pro_month"],
            delay=delay,
        )
