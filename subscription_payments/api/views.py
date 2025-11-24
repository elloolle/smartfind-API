from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, mixins
from dotenv import load_dotenv
import os
import stripe
from subscription_payments.models import Payment, PaymentStatus, Subscription
from .serializers import PaymentSerializer
from loguru import logger
from django.contrib.auth import get_user_model
from django.conf import settings
from ..service import (
    get_event,
    update_user_subscription,
    get_last_user_subscription,
    get_payment_status,
    log_webhooks,
)
from ..helpers import get_subscription_plan_from_product_name
from rest_framework import status

load_dotenv()
stripe.api_key = os.getenv("TEST_STRIPE_API_KEY")

success_url = settings.SUCCESS_URL

User = get_user_model()


class WebhookView(APIView):
    @classmethod
    def get_user_by_customer(cls, customer_id: str):
        try:
            return User.objects.get(customer_id=customer_id)
        except User.DoesNotExist:
            logger.error("Unknown customer_id: {}", customer_id)
            raise

    def post(self, request):
        log_webhooks(request)
        event = get_event(request)
        data = event["data"]["object"]
        event_type = event["type"]
        user = None
        if isinstance(data.get("customer"), str):
            user = self.get_user_by_customer(data["customer"])
        if event_type.startswith("customer.subscription."):
            product_name = data["items"]["data"][0]["price"]["lookup_key"]
            update_user_subscription(
                id=data["id"],
                user=user,
                subscription_status=data["status"],
                product_name=product_name,
            )
        return Response({"status": "success"})


class SubscriptionView(APIView):
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
        Payment.objects.create(
            id=payment_session.id,
            user=self.request.user,
            type=type,
            status=PaymentStatus.pending,
        )
        return Response(payment_session.url)

    def post(self, request):
        subscription = get_last_user_subscription(request.user)
        product_name = request.data.get("product_name")
        if (
            not settings.IGNORE_CLONE_SUBSCRIPTIONS
            and subscription
            and get_subscription_plan_from_product_name(product_name)
            == subscription.plan
        ):
            return Response(
                {"error": "user already subscribed for this plan"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return self.create_payment_link(product_name)

    def delete(self, request):
        user = request.user
        subscription = get_last_user_subscription(user)

        if subscription.plan == settings.PRODUCTS["default_subscription"]["plan"]:
            return Response(
                {"error": "user can't delete default subscription"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        metadata = {
            "collection_method": "send_invoice",
            "days_until_due": settings.DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION,
        }
        stripe.Subscription.modify(subscription.id, metadata=metadata)
        return Response({"status": "success"})


class TrialSubscriptionView(SubscriptionView):
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
    def get(self, request):
        user_payments = Payment.objects.filter(user=request.user).order_by(
            "date_created"
        )
        return Response(PaymentSerializer(user_payments, many=True).data)


# class PaymentMethodView()
