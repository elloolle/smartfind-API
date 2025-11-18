from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, mixins
from dotenv import load_dotenv
import os
import stripe
from subscription_payments.models import Payment, PaymentStatus
from .serializers import PaymentSerializer
from loguru import logger
from django.contrib.auth import get_user_model

load_dotenv()
stripe.api_key = os.getenv("TEST_STRIPE_API_KEY")

success_url = "http://127.0.0.1:8000"
User = get_user_model()


class TestView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"status": "success"})
        # return Response(createPortal(request))


class PaymentView(APIView):
    def get_customer(self) -> str:
        if self.request.user.customer_id:
            return self.request.user.customer_id
        params = {}
        if self.request.user.email:
            params["email"] = self.request.user.email
        if self.request.user.username:
            params["name"] = self.request.user.username
        customer = stripe.Customer.create(**params)

        self.request.user.customer_id = customer.id
        self.request.user.save()
        return customer.id

    def create_session(
        self, mode: str, price: str, metadata=None, url_param=None, **kwargs
    ) -> stripe.checkout.Session:
        session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price": price,
                    "quantity": 1,
                },
            ],
            allow_promotion_codes=True,
            customer=self.get_customer(),
            mode=mode,
            success_url=success_url,
            cancel_url=success_url,
            metadata=metadata,
            **kwargs,
        )
        return session

    @classmethod
    def get_price(cls, key: str) -> str:
        prices = stripe.Price.list(
            lookup_keys=[key],
        )
        return prices.data[0].id

    def create_new_subscription(self, price_name) -> stripe.checkout.Session:
        meta = {"type": price_name}
        return self.create_session(
            "subscription",
            self.get_price(price_name),
            metadata=meta,
            url_param="subscription",
        )

    def get(self, request):
        customer_id = self.get_customer()
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=success_url,
        )
        return Response(portal_session)

    def post(self, request):
        type = request.data.get("type")
        self.get_customer()
        payment_session = self.create_new_subscription(type)
        Payment.objects.create(
            id=payment_session.id,
            user=request.user,
            type=type,
            status=PaymentStatus.pending,
        )
        return Response(payment_session.url)


class WebhookView(APIView):
    def post(self, request):
        pass
