from copy import deepcopy
from datetime import timedelta
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Product, Subscription, SubscriptionStatus

User = get_user_model()


class WebHookViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="yookassa_webhook",
            email="yookassa_webhook@example.com",
            password="strong-password-123",
        )
        self._ensure_products()
        self.url = "/api/yookassa/webhook/"
        self.base_payload = {
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
                    "user_id": str(self.user.id),
                    "cms_name": "yookassa_sdk_python",
                    "product": "pro_month_subscription",
                },
            },
        }

    def _ensure_products(self):
        for product in settings.DEFAULT_PRODUCTS:
            Product.objects.get_or_create(
                name=product["name"],
                defaults={
                    "plan": product.get("plan"),
                    "month_price": product.get("month_price"),
                    "delay": product.get("delay"),
                },
            )

    def _assert_periodic_task(self, payment_method_id, product_id, trial=False):
        task = PeriodicTask.objects.get(name="monthly_job_every_30_days")
        self.assertEqual(task.task, "yookassa_payments.tasks.withdraw_money_for_product")
        kwargs = json.loads(task.kwargs)
        self.assertEqual(kwargs["payment_method_id"], payment_method_id)
        self.assertEqual(kwargs["product_id"], product_id)
        if trial:
            expected_date = (
                timezone.now() + timedelta(days=settings.TRIAL_PERIOD_DAYS)
            ).date()
            self.assertEqual(task.start_time.date(), expected_date)

    def test_webhook_payment_succeeded_creates_subscription_and_task(self):
        payload = deepcopy(self.base_payload)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.product.name, "pro_month_subscription")
        self.assertEqual(
            subscription.id, payload["object"]["payment_method"]["id"]
        )
        self._assert_periodic_task(
            payment_method_id=payload["object"]["payment_method"]["id"],
            product_id=subscription.product_id,
        )
        interval = IntervalSchedule.objects.get(every=30, period=IntervalSchedule.DAYS)
        self.assertEqual(
            PeriodicTask.objects.get(name="monthly_job_every_30_days").interval_id,
            interval.id,
        )

    def test_webhook_trial_payment_succeeded_creates_subscription_and_task(self):
        payload = deepcopy(self.base_payload)
        payload["object"]["metadata"]["trial"] = True

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.product.name, "pro_month_subscription")
        self.assertEqual(
            subscription.id, payload["object"]["payment_method"]["id"]
        )
        self._assert_periodic_task(
            payment_method_id=payload["object"]["payment_method"]["id"],
            product_id=subscription.product_id,
            trial=True,
        )

    def test_webhook_payment_canceled_marks_subscription_unpaid_and_removes_task(self):
        payment_method_id = self.base_payload["object"]["payment_method"]["id"]
        product = Product.objects.get(name="pro_month_subscription")
        subscription = Subscription.objects.create(
            id=payment_method_id,
            user=self.user,
            status=SubscriptionStatus.ACTIVE,
            product=product,
        )
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=30, period=IntervalSchedule.DAYS
        )
        PeriodicTask.objects.create(
            name="monthly_job_every_30_days",
            interval=interval,
            task="yookassa_payments.tasks.withdraw_money_for_product",
            start_time=timezone.now(),
            enabled=True,
            kwargs=json.dumps(
                {"payment_method_id": payment_method_id, "product_id": product.pk},
                sort_keys=True,
            ),
        )
        payload = deepcopy(self.base_payload)
        payload["event"] = "payment.canceled"

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.UNPAID)
        self.assertFalse(
            PeriodicTask.objects.filter(name="monthly_job_every_30_days").exists()
        )
