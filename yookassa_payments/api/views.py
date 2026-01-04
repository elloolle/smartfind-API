from django.conf import settings
from loguru import logger
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from yookassa.domain.notification import WebhookNotification
from ..service import get_subscription_payment, get_subscription_payment_link


def make_task_for_auto_pay(payment_method_id, product):
    pass


class WebHookView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            WebhookNotification(request.body)
        except Exception:
            logger.exception("Webhook notification failed")
        event = request.body
        event_type = event["event"]
        if event_type == "payment.succeed" or "payment.waiting_for_capture":
            payment_method = event["payment_method"]
            product = Product(**event["metadata"]["product"])
            make_task_for_auto_pay(payment_method["id"], event["metadata"]["product"])
        if event_type == "payment.canceled":
            logger.info("Payment canceled")
        return event


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = request.data.get("product_name")
        payment = get_subscription_payment(user_id, product_name)
        return get_subscription_payment_link(payment)
