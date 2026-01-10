from django.conf import settings
from loguru import logger
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from yookassa.domain.notification import WebhookNotification
from ..service import (
    get_subscription_payment,
    get_subscription_payment_link,
    make_auto_pay_every_30_days,
    decline_auto_pay_if_enable,
)


class WebHookView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            WebhookNotification(request.body)
        except Exception as e:
            logger.exception(f"Webhook notification failed: {e}")
        event = request.body
        event_type = event["event"]
        if event_type == "payment.succeed" or "payment.waiting_for_capture":
            payment_method = event["payment_method"]
            product = Product(**event["metadata"]["product"])
            make_auto_pay_every_30_days(payment_method["id"], product)
        if event_type == "payment.canceled":
            payment_method = event["payment_method"]
            decline_auto_pay_if_enable(payment_method["id"])
            logger.info(f"Payment canceled. Payment: {event}")
        return event


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = request.data.get("product_name")
        payment = get_subscription_payment(user_id, product_name)
        return get_subscription_payment_link(payment)
