from __future__ import annotations

import os
from typing import TypedDict

from dotenv import load_dotenv
import stripe


load_dotenv()
stripe.api_key = os.getenv("TEST_STRIPE_API_KEY")


def check_webhook_signature(request):
    try:
        signature = request.headers.get("stripe-signature")
        event = stripe.Webhook.construct_event(
            payload=request.body, sig_header=signature, secret=STRIPE_WEBHOOK_SECRET
        )
    except SignatureVerificationError:
        raise "error in webhook signature"
