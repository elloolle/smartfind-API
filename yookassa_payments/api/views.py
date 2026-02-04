from django.conf import settings
from django.contrib.auth import get_user_model
from loguru import logger
from rest_framework import mixins, viewsets
from rest_framework import status as response_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Product,
    Subscription,
    SubscriptionStatus,
    PaymentMethodStatus,
    PaymentStatus,
)
from .serializers import (
    PaymentSerializer,
    PaymentMethodSerializer,
    EventTypeSerializer,
    PaymentEventSerializer,
)
from ..models import Payment, PaymentMethod
from ..service import (
    get_subscription_payment_link,
    get_trial_subscription_payment_link,
    make_auto_pay,
    make_once_pay,
    delete_subscription_and_autopay,
    delete_subscription_and_autopay_by_user,
    log_payment_method_into_db,
)

User = get_user_model()


YOOKASSA_TO_CORE_PAYMENT_STATUS = {
    "succeeded": PaymentStatus.PAID,
    "canceled": PaymentStatus.UNPAID,
}

YOOKASSA_TO_CORE_PAYMENT_METHOD_STATUS = {
    "active": PaymentMethodStatus.ACTIVE,
    "succeeded": PaymentMethodStatus.ACTIVE,
    "canceled": PaymentMethodStatus.CANCELED,
}


class WebHookView(APIView):
    def process_first_payment(self):
        self.sub.delete()
        product = Product.objects.filter(name=self.product_name).first()
        Subscription.objects.create(
            user=self.user,
            status=SubscriptionStatus.ACTIVE,
            product=product,
        )
        make_auto_pay(self.payment_method, product)

    def process_auto_pay_payment(self):
        product_delay = self.sub.product.delay
        self.sub.end_period += product_delay

    def process_success_payment(self):
        if self.is_auto_pay:
            self.process_auto_pay_payment()
        else:
            self.process_first_payment()

    def process_canceled_payment(self):
        if not self.is_auto_pay:
            # значит это неуспешная попытка первого платежа
            return
        delete_subscription_and_autopay(self.sub)

    def log_payment_into_db(self, payment_json):
        status = YOOKASSA_TO_CORE_PAYMENT_STATUS[self.event_status]
        income_amount = 0
        if self.event_type == "succeeded":
            income_amount = payment_json["income_amount"]["value"]
        Payment.objects.update_or_create(
            id=payment_json["id"],
            defaults={
                "user": self.user,
                "status": status,
                "amount": payment_json["amount"]["value"],
                "income_amount": income_amount,
            },
        )

    def process_payment_method(self, payment_method_json):
        if self.event_type == "canceled":
            return
        payment_method = log_payment_method_into_db(
            payment_method_json,
            self.user,
            YOOKASSA_TO_CORE_PAYMENT_METHOD_STATUS[self.event_status],
        )
        self.payment_method = payment_method

    def process_payment_event(self, event):
        serializer = PaymentEventSerializer(data={"event": event})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        self.user = validated_data["user"]
        self.sub = validated_data["sub"]
        self.product_name = validated_data["product_name"]
        self.is_auto_pay = validated_data["is_auto_pay"]
        payment_json = validated_data["obj"]

        self.log_payment_into_db(payment_json)
        self.process_payment_method(payment_json["payment_method"])

        if self.event_type in ("payment.succeeded", "payment.waiting_for_capture"):
            self.process_success_payment()
        if self.event_type == "payment.canceled":
            self.process_canceled_payment()

    def process_payment_method_saved(self, event):
        payment_method = PaymentMethod.objects.get(id=event["object"]["id"])
        status = YOOKASSA_TO_CORE_PAYMENT_METHOD_STATUS[self.event_status]
        payment_method.status = status
        user = payment_method.user
        product = Product.objects.get(name=settings.TRIAL_PRODUCT_NAME)
        Subscription.objects.filter(user=user).delete()
        Subscription.objects.create(
            user=user,
            status=SubscriptionStatus.ACTIVE,
            product=product,
        )
        product_after_trial = Product.objects.get(
            name=settings.PRODUCT_NAME_AFTER_TRIAL_PERIOD
        )
        make_once_pay(payment_method, product_after_trial, pay_delay=product.delay)

    def post(self, request, *args, **kwargs):
        event = request.data
        logger.info(f"webhook request: {event}")
        serializer = EventTypeSerializer(data={"event": event})
        serializer.is_valid(raise_exception=True)
        self.event_type = serializer.validated_data["event_type"]
        self.event_status = self.event_type.split(".", 1)[1]
        if self.event_type.startswith("payment."):
            self.process_payment_event(event)
        if self.event_type == "payment_method.active":
            # этот вебхук отправляется только в случае привязки платежных
            # средств для trial подписки
            self.process_payment_method_saved(event)
        return Response(status=response_status.HTTP_200_OK)


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        user_id = user.id
        product_name = request.data.get("product_name")
        if user.subscription.product_name != product_name or settings.DEBUG:
            return Response(get_subscription_payment_link(user_id, product_name))
        return Response(
            {"message": "The user has already subscription"},
            status=response_status.HTTP_403_FORBIDDEN,
        )


class TrialSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if settings.DEBUG:
            user_id = request.user.id
            product_name = settings.TRIAL_PRODUCT_NAME
            return Response(get_trial_subscription_payment_link(user_id, product_name))

        if not user.may_have_trial:
            return Response(
                {"message": "The user has already signed up for a trial subscription."},
                status=response_status.HTTP_403_FORBIDDEN,
            )
        if user.subscription.product_name != settings.DEFAULT_PRODUCT_NAME:
            return Response(
                {"message": "The user has already subscription"},
                status=response_status.HTTP_403_FORBIDDEN,
            )
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

    def perform_destroy(self, instance):
        delete_subscription_and_autopay_by_user(self.request.user)
        instance.status = PaymentMethodStatus.CANCELED

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)


class PaymentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
