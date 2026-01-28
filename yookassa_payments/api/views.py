from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from ..helpers import make_anonymous_card
from loguru import logger
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from datetime import timedelta

from core.models import (
    Product,
    Subscription,
    SubscriptionStatus,
    PaymentMethodStatus,
    PaymentStatus,
)
from ..service import (
    get_subscription_payment_link,
    get_trial_subscription_payment_link,
    make_auto_pay,
    make_trial_auto_pay,
    decline_subscription,
    decline_subscription_by_user,
)
from .serializers import (
    PaymentSerializer,
    PaymentMethodSerializer,
    EventTypeSerializer,
    PaymentEventSerializer,
)
from ..models import Payment, PaymentMethod
from rest_framework import mixins, viewsets
from core.helpers import now

User = get_user_model()


YOOKASSA_TO_CORE_PAYMENT_STATUS = {
    "succeeded": PaymentStatus.PAID,
    "canceled": PaymentStatus.UNPAID,
}

YOOKASSA_TO_CORE_PAYMENT_METHOD_STATUS = {
    "succeeded": PaymentMethodStatus.ACTIVE,
    "canceled": PaymentMethodStatus.CANCELED,
}


def get_details_from_payment_method(payment_method):
    details = {"type": payment_method["type"]}
    if payment_method["type"] == "yoo_money":
        details["number"] = payment_method["account_number"]
    elif payment_method["type"] == "bank_card":
        card = payment_method["card"]
        details["number"] = make_anonymous_card(card["first6"], card["last4"])
        details["expire_date"] = f"{card["expiry_month"]}/{card["expiry_year"][2:4]}"
    else:
        logger.exception(f"Payment method not supported: {payment_method}")
    return details


class WebHookView(APIView):
    def process_subscription(self):
        sub = self.sub
        if (
            not sub
            or sub.status != SubscriptionStatus.ACTIVE
            or sub.product.name == settings.DEFAULT_PRODUCT_NAME
        ):
            if sub:
                sub.delete()
            Subscription.objects.create(
                user=self.user,
                status=SubscriptionStatus.ACTIVE,
                product=self.product,
            )
            make_auto_pay(self.payment_method, self.product)

    def process_trial_subscription(self):
        if self.sub:
            self.sub.delete()
        Subscription.objects.create(
            user=self.user,
            status=SubscriptionStatus.ACTIVE,
            product=self.product,
        )
        make_trial_auto_pay(self.payment_method, self.product)

    def process_success_payment(self, obj):
        metadata = obj["metadata"]
        if metadata.get("autopay"):
            self.sub.end_period += timedelta(days=settings.DAYS_IN_MONTH)
            return
        product = Product.objects.filter(name=metadata.get("product")).first()
        if not product:
            return
        self.product = product
        if metadata.get("trial"):
            self.process_trial_subscription()
        else:
            self.process_subscription()

    def process_canceled_payment(self, obj):
        if not self.sub:
            return
        decline_subscription(self.sub)

    def log_payment_method_into_db(self, payment_method):
        status = YOOKASSA_TO_CORE_PAYMENT_METHOD_STATUS[self.event_status]
        details = get_details_from_payment_method(payment_method)

        payment_method_obj, _ = PaymentMethod.objects.update_or_create(
            id=payment_method["id"],
            defaults={"user": self.user, "status": status, "details": details},
        )
        self.payment_method = payment_method_obj

    def log_payment_into_db(self, payment):
        status = YOOKASSA_TO_CORE_PAYMENT_STATUS[self.event_status]
        Payment.objects.update_or_create(
            id=payment["id"],
            defaults={
                "user": self.user,
                "status": status,
                "amount": payment["amount"]["value"],
                "income_amount": payment["income_amount"]["value"],
            },
        )

    def process_payment_event(self, event):
        serializer = PaymentEventSerializer(data={"event": event})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        self.user = validated_data["user"]
        self.sub = validated_data["sub"]
        self.event_status = validated_data["event_status"]
        obj = validated_data["obj"]

        self.log_payment_into_db(obj)
        self.log_payment_method_into_db(obj["payment_method"])
        if self.event_type in ("payment.succeeded", "payment.waiting_for_capture"):
            self.process_success_payment(obj)
        if self.event_type == "payment.canceled":
            self.process_canceled_payment(obj)

    def post(self, request, *args, **kwargs):
        event = request.data
        logger.info(f"webhook request: {event}")
        serializer = EventTypeSerializer(data={"event": event})
        serializer.is_valid(raise_exception=True)
        self.event_type = serializer.validated_data["event_type"]
        if self.event_type.startswith("payment."):
            self.process_payment_event(event)
        return Response(status=status.HTTP_200_OK)


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = request.data.get("product_name")
        return Response(get_subscription_payment_link(user_id, product_name))

    def delete(self, request, *args, **kwargs):
        decline_subscription_by_user(request.user)


class TrialSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = settings.TRIAL_PRODUCT_NAME
        return Response(get_trial_subscription_payment_link(user_id, product_name))


class PaymentMethodViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def perform_destroy(self, payment_method):
        decline_subscription_by_user(self.request.user)
        payment_method.delete()

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)


class PaymentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
