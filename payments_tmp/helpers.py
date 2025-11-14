import stripe
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from bitapi.payments.models import StripeSubscription
from bitapi.users.models import User
from config.configuration import FRONT_URL

User = get_user_model()


def get_user_sub_db(user: User) -> StripeSubscription | None:
    # Get last not canceled subscription
    return (
        StripeSubscription.objects.filter(~Q(status="canceled"), user=user)
        .order_by("date_created")
        .last()
    )


def get_current_sub(user: User) -> stripe.Subscription | None:
    sub = get_user_sub_db(user)
    if not sub:
        return None
    return stripe.Subscription.retrieve(sub.id)


def is_more_expensive(sub: str, prev_sub: str) -> bool:
    order = ["free", "premium", "pro", "enterprise"]
    return order.index(sub) > order.index(prev_sub)


def get_price(subscription: dict) -> str:
    return subscription["items"]["data"][-1]["price"]["lookup_key"]


def get_customer_session_url(user) -> str:
    return stripe.billing_portal.Session.create(
        customer=user.customer_id,
        return_url=f"{FRONT_URL}/main/subscription",
    ).url


def grant_credits(user: User):
    if not user.customer_id:
        return

    try:
        with transaction.atomic():
            obj = User.objects.select_for_update().get(pk=user.id)
            grant_credits_cents = obj.grant_credits_cents
            if not grant_credits_cents:
                return
            obj.grant_credits_cents = 0
            obj.save()

            customer = stripe.Customer.retrieve(user.customer_id)
            stripe.Customer.modify(
                user.customer_id, balance=customer["balance"] - grant_credits_cents
            )
    except Exception:
        logger.exception("Error granting credits {}", user.username)


PRICE_NAME_MAP = {
    "premium": "Premium",
    "pro": "Pro",
    "enterprise": "Enterprise",
    "free": "Free",
    "pay_as_you_go": "Pay as you go",
}


def sub2plan(name: str) -> str:
    return name.lower().replace(" ", "_")
