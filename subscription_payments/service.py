from __future__ import annotations


import stripe

from django.conf import settings
from loguru import logger
from django.contrib.auth import get_user_model
from djstripe.models import Subscription, Customer
from core.models import SubscriptionStatus, Product
from core.models import Subscription as CoreSubscription
from datetime import datetime, timedelta
from core.helpers import get_datetime_from_unix_timestamp
from django.utils import timezone

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


def get_core_sub_dict_from_djstripe_sub(djstripe_sub):
    id = djstripe_sub.id
    product_name = djstripe_sub.stripe_data["items"]["data"][0]["price"]["lookup_key"]
    user = User.objects.get(customer_id=djstripe_sub.customer.id)
    djstripe_sub_status = djstripe_sub.status
    STRIPE_TO_CORE_STATUS = {
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.UNPAID,
        "canceled": SubscriptionStatus.UNPAID,
        "unpaid": SubscriptionStatus.UNPAID,
        "incomplete": SubscriptionStatus.UNPAID,
        "incomplete_expired": SubscriptionStatus.UNPAID,
    }
    status = STRIPE_TO_CORE_STATUS.get(djstripe_sub_status, SubscriptionStatus.UNPAID)

    start_period = get_datetime_from_unix_timestamp(djstripe_sub.start_date)
    if not djstripe_sub.ended_at:
        end_period = None
    else:
        end_period = get_datetime_from_unix_timestamp(djstripe_sub.ended_at)
    product = Product.objects.get(name=product_name)
    return {
        "id": id,
        "user": user,
        "status": status,
        "start_period": start_period,
        "end_period": end_period,
        "product": product,
    }
