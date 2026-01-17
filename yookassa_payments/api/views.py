from django.conf import settings
from numpy.f2py.auxfuncs import throw_error
from rest_framework.response import Response
from rest_framework import status
from ..helpers import make_anonymous_card
from loguru import logger
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from yookassa.domain.notification import WebhookNotification
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
)
from .serializers import PaymentSerializer, PaymentMethodSerializer
from ..models import Payment, PaymentMethod
from rest_framework import mixins, viewsets
from core.helpers import now

User = get_user_model()


YOOKASSA_TO_CORE_STATUS = {
    "succeeded": PaymentStatus.PAID,
    "canceled": PaymentStatus.UNPAID,
}


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
                id=self.payment_method.id,
                user=self.user,
                status=SubscriptionStatus.ACTIVE,
                product=self.product,
            )
            make_auto_pay(self.payment_method, self.product)

    def process_trial_subscription(self):
        if self.sub:
            self.sub.delete()
        Subscription.objects.create(
            id=self.payment_method.id,
            user=self.user,
            status=SubscriptionStatus.ACTIVE,
            product=self.product,
        )
        make_trial_auto_pay(self.payment_method, self.product)

    def process_success_payment(self, obj):
        metadata = obj["metadata"]
        if metadata.get("autopay"):
            return
        product = Product.objects.filter(name=metadata["product"]).first()
        if not product:
            logger.exception(f"Product not found: {metadata['product']}")
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
        status = YOOKASSA_TO_CORE_STATUS[self.event_status]
        details = {"type": payment_method["type"]}

        if payment_method["type"] == "yoo_money":
            details["number"] = payment_method["account_number"]
        elif payment_method["type"] == "bank_card":
            card = payment_method["card"]
            details["number"] = make_anonymous_card(card["first6"], card["last4"])
            details["expire_date"] = (
                f"{card["expiry_month"]}/{card["expiry_year"][2:4]}"
            )
        else:
            logger.exception(f"Payment method not supported: {self.request.data}")
        payment_method_obj, _ = PaymentMethod.objects.update_or_create(
            id=payment_method["id"],
            defaults={"user": self.user, "status": status, "details": details},
        )
        self.payment_method = payment_method_obj

    def log_payment_into_db(self, payment):
        status = YOOKASSA_TO_CORE_STATUS[self.event_status]
        Payment.objects.update_or_create(
            id=payment["id"],
            defaults={
                "user": self.user,
                "status": status,
                "period_start": now(),
                "amount": payment["amount"]["value"],
                "income_amount": payment["income_amount"]["value"],
            },
        )

    def process_payment_event(self, event):
        obj = event["object"]
        metadata = obj["metadata"]
        user_id = metadata.get("user_id")
        user = User.objects.filter(id=user_id).first()
        if not user:
            logger.exception(f"User not found: {user_id}")
        self.user = user
        self.sub = Subscription.objects.filter(user=self.user).first()
        self.event_status = self.event_type.removeprefix("payment.")

        self.log_payment_into_db(obj)
        self.log_payment_method_into_db(obj["payment_method"])
        if self.event_type in ("payment.succeeded", "payment.waiting_for_capture"):
            self.process_success_payment(obj)
        if self.event_type == "payment.canceled":
            self.process_canceled_payment(obj)

    def post(self, request, *args, **kwargs):
        logger.info(f"webhook request: {request.data}")
        event = request.data
        try:
            WebhookNotification(event)
        except Exception as e:
            logger.exception(f"Webhook notification failed: {e}")
        self.event_type = event["event"]
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
        subscription = Subscription.objects.get(user=request.user)
        decline_subscription(subscription)


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

    # TODO добавить возможность удаления paymentMethod
    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)


class PaymentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


a = {
    "type": "notification",
    "event": "payment.succeeded",
    "object": {
        "id": "30fd6026-000f-5001-8000-1e78969d3895",
        "status": "succeeded",
        "amount": {"value": "100.00", "currency": "RUB"},
        "income_amount": {"value": "95.73", "currency": "RUB"},
        "recipient": {"account_id": "1239880", "gateway_id": "2617846"},
        "payment_method": {
            "type": "bank_card",
            "id": "30fd6026-000f-5001-8000-1e78969d3895",
            "saved": True,
            "status": "active",
            "title": "Bank card *4444",
            "card": {
                "first6": "555555",
                "last4": "4444",
                "expiry_year": "2030",
                "expiry_month": "11",
                "card_type": "MasterCard",
                "card_product": {"code": "E"},
                "issuer_country": "US",
            },
        },
        "captured_at": "2026-01-17T08:46:45.712Z",
        "created_at": "2026-01-17T08:46:30.538Z",
        "test": True,
        "refunded_amount": {"value": "0.00", "currency": "RUB"},
        "paid": True,
        "refundable": True,
        "metadata": {
            "user_id": "1",
            "cms_name": "yookassa_sdk_python",
            "product": "pro_month_subscription",
        },
        "authorization_details": {
            "rrn": "685777020785792",
            "auth_code": "704516",
            "three_d_secure": {
                "applied": False,
                "method_completed": False,
                "challenge_completed": False,
            },
        },
    },
}

b = {
    "type": "notification",
    "event": "payment.succeeded",
    "object": {
        "id": "30f5d918-000f-5001-9000-14efbe8f8527",
        "status": "succeeded",
        "amount": {"value": "100.00", "currency": "RUB"},
        "income_amount": {"value": "95.73", "currency": "RUB"},
        "recipient": {"account_id": "1239880", "gateway_id": "2617846"},
        "payment_method": {
            "type": "yoo_money",
            "id": "30f5d918-000f-5001-9000-14efbe8f8527",
            "saved": True,
            "status": "active",
            "title": "YooMoney wallet 410011758831136",
            "account_number": "410011758831136",
        },
        "captured_at": "2026-01-11T15:44:35.557Z",
        "created_at": "2026-01-11T15:44:24.482Z",
        "test": True,
        "refunded_amount": {"value": "0.00", "currency": "RUB"},
        "paid": True,
        "refundable": True,
        "metadata": {
            "user_id": "2",
            "cms_name": "yookassa_sdk_python",
            "product": "pro_month_subscription",
        },
    },
}
