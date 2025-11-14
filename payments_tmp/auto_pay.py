import stripe
from loguru import logger

from bitapi.payments.helpers import get_user_sub_db
from bitapi.payments.models import StripeSubscription
from bitapi.utils import send_telegram_notification
from bitapi.utils import get_limits

from bitapi.users.models import User


class AutoPayService:

    @classmethod
    def buy(cls, pay_amount: int, customer_id: str):
        customer = stripe.Customer.retrieve(customer_id)
        pm_id = customer.get("invoice_settings", {}).get("default_payment_method")
        if not pm_id:
            payment_methods = stripe.PaymentMethod.list(customer=customer_id)
            pm_count = len(payment_methods.data)
            if pm_count == 0:
                logger.warning("No payment methods for {}", customer_id)
                raise Exception("No payment methods found")
            pm_id = payment_methods.data[0]["id"]

        payment = stripe.PaymentIntent.create(
            amount=pay_amount,
            customer=customer_id,
            payment_method=pm_id,
            confirm=True,
            off_session=True,
            currency="usd",
            metadata={"type": "auto_pay"},
        )
        status = payment["status"]
        if status == "requires_payment_method":
            logger.warning("Payment failed {}", payment.id)
            raise Exception("No available payment methods")

        if status == "succeeded":
            logger.info("Payment succeeded {}", payment.id)
            return True

        logger.error("Payment unknown status {}", payment.status)
        raise Exception("Payment unknown status")

    @classmethod
    def add_limits(cls, user: User, amount: int):
        logger.info("Adding {} words to user {}", amount, user.id)
        user.additional_limits = {
            **(user.additional_limits or {}),
            "granted_words_simple_scan": user.additional_limits.get(
                "granted_words_simple_scan", 0
            )
            + amount,
        }
        user.save(update_fields=["additional_limits"])

    @classmethod
    def execute_auto_pay(cls, user: User, subscription: StripeSubscription) -> bool:
        price_cents = user.get_limit("extra_words_price") * 100
        try:
            cls.buy(price_cents, user.customer_id)
        except Exception as e:
            subscription.auto_pay["enabled"] = False
            subscription.auto_pay["error"] = str(e)
            subscription.save(update_fields=["auto_pay"])
            logger.warning("AutoPay failed for subscription {}", subscription.id)
            send_telegram_notification(
                f"AutoPay failed user: {user.id} {user.username}"
            )
            return False

        logger.info("AutoPay succeeded for subscription {}", subscription.id)
        add_amount = subscription.auto_pay.get("add_amount")
        if user.subscription_name() != "Enterprise":
            add_amount = get_limits("Pay as you go", "granted_words_simple_scan")

        cls.add_limits(user, add_amount)
        return True

    @classmethod
    def update(cls, user: User, remaining=None) -> bool:
        if not user.customer_id:
            return False
        subscription = get_user_sub_db(user)
        if not subscription:
            return False
        if not subscription.auto_pay:
            logger.info("No AutoPay for subscription enabled {}", subscription.id)
            return False
        if not subscription.auto_pay.get("enabled"):
            logger.info("AutoPay not enabled for subscription {}", subscription.id)
            return False

        subscription = get_user_sub_db(user)
        auto_pay = subscription.auto_pay
        limit = auto_pay.get("limit")
        if not remaining:
            remaining = user.get_remaining_limit("words_simple_scan")
        if remaining < limit:
            return cls.execute_auto_pay(user, subscription)
        else:
            logger.debug(
                "AutoPay not needed, remaining: {}, limit: {}", remaining, limit
            )
            return False
