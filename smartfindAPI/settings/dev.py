from .base import *
import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = True
PAYMENT_VARIANTS = {
    "stripe": (
        "payments.stripe.StripeProviderV3",
        {
            "api_key": os.getenv("TEST_STRIPE_API_KEY"),
            "use_token": True,
            "secure_endpoint": False,
        },
    )
}
