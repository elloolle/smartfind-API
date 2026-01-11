from django.conf import settings
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


class WebHookView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            WebhookNotification(request.body)
        except Exception as e:
            logger.exception(f"Webhook notification failed: {e}")
        event = request.body
        event_type = event["event"]
        if event_type == "payment.succeed" or "payment.waiting_for_capture":
            # TODO сделать обработку вебхуков для trial sub
            payment_method = event["payment_method"]
            try:
                product = Product.objects.get(name=event["metadata"]["product"])
            except Product.DoesNotExist:
                logger.exception(f"Product not found: {event['metadata']['product']}")
                return Response(status=status.HTTP_404_NOT_FOUND)
            Subscription.objects.create(
                id=payment_method["id"],
                user=request.user,
                status=SubscriptionStatus.ACTIVE,
                start_period=now(),
                product=product,
            )
            make_auto_pay_every_30_days(payment_method["id"], product)
        if event_type == "payment.canceled":
            payment_method = event["payment_method"]
            subscription = Subscription.objects.get(id=payment_method["id"])
            subscription.status = SubscriptionStatus.UNPAID
            decline_auto_pay(payment_method["id"])
        return event


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = request.data.get("product_name")
        return get_subscription_payment_link(user_id, product_name)


class TrialSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        product_name = settings.TRIAL_PRODUCT_NAME
        return get_trial_subscription_payment_link(user_id, product_name)
