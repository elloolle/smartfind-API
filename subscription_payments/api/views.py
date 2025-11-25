from django.core.serializers import serialize
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework import viewsets, mixins
from dotenv import load_dotenv
import os
import stripe
from loguru import logger
from django.contrib.auth import get_user_model
from django.conf import settings

from .serializers import SubscriptionProductNameSerializer
from ..service import (
    get_last_user_subscription,
)
from rest_framework import status

load_dotenv()
stripe.api_key = os.getenv("TEST_STRIPE_API_KEY")

success_url = settings.SUCCESS_URL

User = get_user_model()


class SubscriptionView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionProductNameSerializer

    def get_customer(self) -> str:
        return self.request.user.customer_id

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

    def create_new_subscription(
        self, price_name, trial_period_days
    ) -> stripe.checkout.Session:
        meta = {"type": price_name}
        if trial_period_days == 0:
            trial_period_days = None
        return self.create_session(
            "subscription",
            self.get_price(price_name),
            metadata=meta,
            url_param="subscription",
            subscription_data={"trial_period_days": trial_period_days},
        )

    def create_payment_link(self, product_name, trial_period_days=0):
        self.get_customer()
        payment_session = self.create_new_subscription(product_name, trial_period_days)
        return Response(payment_session.url)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_name = serializer.data["product_name"]
        return self.create_payment_link(product_name)

    def delete(self, request):
        user = request.user
        subscription = get_last_user_subscription(user)
        if not subscription:
            return Response(
                {"error": "user can't delete default subscription"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        metadata = {
            "collection_method": "send_invoice",
            "days_until_due": settings.DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION,
        }
        stripe.Subscription.modify(subscription.id, metadata=metadata)
        return Response({"status": "success"})


class TrialSubscriptionView(SubscriptionView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.may_have_trial:
            return Response(
                {"error": "user does not have trial permissions"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        user = request.user
        user.may_have_trial = False
        user.save()
        return self.create_payment_link(
            product_name=settings.DEFAULT_TRIAL_PLAN,
            trial_period_days=settings.TRIAL_PERIOD_DAYS,
        )


class CustomerPortalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_id = request.user.customer_id
        if not customer_id:
            return Response(
                {"error": "user does not buy subscriptions"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=success_url,
        )
        return Response({"portal_session_link": portal_session.url})


class PaymentView(APIView):
    permission_classes = [IsAuthenticated]


# class PaymentMethodView()
