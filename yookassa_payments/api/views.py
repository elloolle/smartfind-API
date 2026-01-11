from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

from loguru import logger
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from yookassa.domain.notification import WebhookNotification
from core.helpers import now
from core.models import Product, Subscription, SubscriptionStatus
from ..service import (
    get_subscription_payment_link,
    get_subscription_payment_link,
    make_auto_pay_every_30_days,
    decline_auto_pay,
    get_trial_subscription_payment_link,
)


def process_success_payment(obj):
    payment_method = obj["payment_method"]
    try:
        product = Product.objects.get(name=obj["metadata"]["product"])
    except Product.DoesNotExist:
        logger.exception(f"Product not found: {obj['metadata']['product']}")
        return Response("product not found", status=status.HTTP_404_NOT_FOUND)
    sub = Subscription.objects.filter(user=request.user).first()
    if (
        not sub
        or sub.status != SubscriptionStatus.ACTIVE
        or sub.product.name != settings.DEFAULT_PRODUCT_NAME
    ):
        if sub:
            sub.delete()
        Subscription.objects.create(
            id=payment_method["id"],
            user=request.user,
            status=SubscriptionStatus.ACTIVE,
            start_period=now(),
            product=product,
        )
        make_auto_pay_every_30_days(payment_method["id"], product)


def process_canceled_payment(obj):
    payment_method = obj["payment_method"]
    subscription = Subscription.objects.get(id=payment_method["id"])
    subscription.status = SubscriptionStatus.UNPAID
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
        if event_type == "payment.succeed" or "payment.waiting_for_capture":
            # TODO сделать обработку вебхуков для trial sub
            process_success_payment(obj)
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
