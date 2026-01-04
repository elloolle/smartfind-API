from django.conf import settings
from loguru import logger
import uuid

from yookassa import Configuration, Payment

Configuration.account_id = settings.YOOKASSA_ACCOUNT_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

print(payment.json())


def make_payment(user_id, amount, metadata):
    payment = Payment.create(
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


def get_subscription_payment_link(payment):
    return payment.confirmation.confirmation_url


def get_subscription_payment(user_id, subscription_type):
    product = settings.PRODUCTS[subscription_type]
    metadata = {"user_id": user_id, "product": asdict(product)}
    payment = make_payment(user_id, product.month_price, metadata)
    return payment
