import stripe
from dotenv import load_dotenv
import os
from loguru import logger

load_dotenv()
stripe.api_key = os.getenv("TEST_STRIPE_API_KEY")


class StripeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.debug(request.user)

        if request.user.is_authenticated and request.path.startswith("/api/payments/"):
            params = {}
            if request.user.email:
                params["email"] = request.user.email
            if request.user.username:
                params["name"] = request.user.username
            customer = stripe.Customer.create(**params)
            request.user.customer_id = customer.id
            request.user.save()
        response = self.get_response(request)
        return response
