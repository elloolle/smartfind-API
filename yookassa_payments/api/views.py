from django.conf import settings
from numpy.f2py.auxfuncs import throw_error
from rest_framework.response import Response
from rest_framework import status

from loguru import logger
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from yookassa.domain.notification import WebhookNotification
from core.models import Product, Subscription, SubscriptionStatus
from ..service import (
    get_subscription_payment_link,
    decline_auto_pay,
    get_trial_subscription_payment_link,
    make_auto_pay,
    make_trial_auto_pay,
)

User = get_user_model()


def process_subscription(obj, product, sub, user):
    payment_method = obj["payment_method"]
    if (
        not sub
        or sub.status != SubscriptionStatus.ACTIVE
        or sub.product.name == settings.DEFAULT_PRODUCT_NAME
    ):
        if sub:
            sub.delete()
        Subscription.objects.create(
            id=payment_method["id"],
            user=user,
            status=SubscriptionStatus.ACTIVE,
            product=product,
        )
        make_auto_pay(payment_method["id"], product)


def process_trial_subscription(obj, product, sub, user):
    payment_method = obj["payment_method"]
    sub = Subscription.objects.filter(user=user).first()
    if sub:
        sub.delete()
    Subscription.objects.create(
        id=payment_method["id"],
        user=user,
        status=SubscriptionStatus.ACTIVE,
        product=product,
    )
    make_trial_auto_pay(payment_method["id"], product)


def process_success_payment(obj, user=None):
    metadata = obj["metadata"]
    if not user or not getattr(user, "is_authenticated", False):
        user_id = metadata.get("user_id")
        if user_id:
            user = User.objects.filter(id=user_id).first()
    if not user:
        logger.error("Webhook payment missing user")
        return
    try:
        product = Product.objects.get(name=metadata["product"])
    except Product.DoesNotExist:
        logger.exception(f"Product not found: {metadata['product']}")
        raise Exception(Response("product not found", status=status.HTTP_404_NOT_FOUND))
    sub = Subscription.objects.filter(user=user).first()

    if metadata.get("trial"):
        process_trial_subscription(obj, product, sub, user)
    else:
        process_subscription(obj, product, sub, user)


def process_canceled_payment(obj):
    payment_method = obj["payment_method"]
    subscription = Subscription.objects.get(id=payment_method["id"])
    subscription.status = SubscriptionStatus.UNPAID
    subscription.save(update_fields=["status"])
    decline_auto_pay(payment_method["id"])


class WebHookView(APIView):
    def post(self, request, *args, **kwargs):
        logger.info(f"webhook request: {request.data}")
        try:
            WebhookNotification(request.data)
        except Exception as e:
            logger.exception(f"Webhook notification failed: {e}")
        event = request.data
        event_type = event["event"]
        obj = event["object"]
        if event_type in ("payment.succeeded", "payment.waiting_for_capture"):
            process_success_payment(obj, request.user)
        if event_type == "payment.canceled":
            process_canceled_payment(obj)
        return Response(status=status.HTTP_200_OK)


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = request.data.get("product_name")
        return Response(get_subscription_payment_link(user_id, product_name))


class TrialSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = settings.TRIAL_PRODUCT_NAME
        return Response(get_trial_subscription_payment_link(user_id, product_name))
