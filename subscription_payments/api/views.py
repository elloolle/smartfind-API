from django.core.serializers import serialize
from djstripe.models import PaymentMethod, Invoice
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework import viewsets, mixins
import stripe
from loguru import logger
from django.contrib.auth import get_user_model
from django.conf import settings

from .serializers import (
    SubscriptionProductNameSerializer,
    PaymentMethodSerializer,
    InvoiceSerializer,
    CheckSubscriptionExistsSerializer,
)
from ..service import (
    get_last_user_subscription,
)
from rest_framework import status

stripe.api_key = settings.STRIPE_SECRET_KEY

User = get_user_model()


class EnsureStripeCustomerMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.customer_id:
            params = {}
            if request.user.username:
                params["name"] = request.user.username
            customer = stripe.Customer.create(**params)
            request.user.customer_id = customer.id
            request.user.save()


class SubscriptionView(EnsureStripeCustomerMixin, GenericAPIView):
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
            success_url=settings.CHECKOUT_SUCCESS_URL,
            cancel_url=settings.CHECKOUT_CANCEL_URL,
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
        payment_session = self.create_new_subscription(product_name, trial_period_days)
        return Response(payment_session.url)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SubscriptionProductNameSerializer
        elif self.request.method == "DELETE":
            return CheckSubscriptionExistsSerializer
        else:
            raise f"serializer_class don't exists for {self.request.method}"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_name = serializer.data["product_name"]
        return self.create_payment_link(product_name)

    def delete(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription_id = serializer.subscription_id
        stripe.Subscription.modify(
            subscription_id,
            collection_method="send_invoice",
            days_until_due=settings.DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION,
        )
        return Response({"status": "success"})


class TrialSubscriptionView(SubscriptionView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # TODO валидация
        if not request.user.may_have_trial:
            return Response(
                {"error": "user does not have trial permissions"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user.may_have_trial = True
        user.save()
        return self.create_payment_link(
            product_name=settings.DEFAULT_TRIAL_PLAN,
            trial_period_days=settings.TRIAL_PERIOD_DAYS,
        )


class CustomerPortalView(EnsureStripeCustomerMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portal_session = stripe.billing_portal.Session.create(
            customer=request.user.customer_id,
            return_url=settings.PORTAL_SUCCESS_URL,
        )
        return Response({"portal_session_link": portal_session.url})


class PaymentMethodViewSet(
    EnsureStripeCustomerMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        customer_id = self.request.user.customer_id
        return PaymentMethod.objects.filter(customer=customer_id)


class PaymentViewSet(
    EnsureStripeCustomerMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        customer_id = self.request.user.customer_id
        return Invoice.objects.filter(customer=customer_id)
