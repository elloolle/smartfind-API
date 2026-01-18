from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from rest_framework import status
from rest_framework.test import APITestCase

from unittest.mock import patch

from core.models import (
    PaymentMethodStatus,
    PaymentStatus,
    Product,
    Subscription,
    SubscriptionStatus,
)
from yookassa_payments.models import Payment, PaymentMethod
from ..service import PAYMENT_JOB_NAME

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

    def _assert_periodic_task(self, payment_method_id, amount, user_id, trial=False):
        task = PeriodicTask.objects.get(name=f"{PAYMENT_JOB_NAME}_{payment_method_id}")
        self.assertEqual(task.task, "yookassa_payments.tasks.withdraw_money")
        kwargs = json.loads(task.kwargs)
        self.assertEqual(kwargs["payment_method_id"], payment_method_id)
        self.assertEqual(kwargs["amount"], amount)
        self.assertEqual(kwargs["metadata"], {"user_id": user_id, "auto_pay": True})
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
        self.assertEqual(subscription.id, payload["object"]["payment_method"]["id"])
        self._assert_periodic_task(
            payment_method_id=payload["object"]["payment_method"]["id"],
            amount=subscription.product.month_price,
            user_id=self.user.id,
        )
        interval = IntervalSchedule.objects.get(
            every=settings.DAYS_IN_MONTH, period=IntervalSchedule.DAYS
        )
        self.assertEqual(
            PeriodicTask.objects.get(
                name=f"{PAYMENT_JOB_NAME}_{payload['object']['payment_method']['id']}"
            ).interval_id,
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
        self.assertEqual(subscription.id, payload["object"]["payment_method"]["id"])
        self._assert_periodic_task(
            payment_method_id=payload["object"]["payment_method"]["id"],
            amount=subscription.product.month_price,
            user_id=self.user.id,
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
            every=settings.DAYS_IN_MONTH, period=IntervalSchedule.DAYS
        )
        PeriodicTask.objects.create(
            name=f"{PAYMENT_JOB_NAME}_{payment_method_id}",
            interval=interval,
            task="yookassa_payments.tasks.withdraw_money",
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
            PeriodicTask.objects.filter(
                name=f"{PAYMENT_JOB_NAME}_{payment_method_id}"
            ).exists()
        )

    @patch("yookassa_payments.api.views.now")
    def test_webhook_logs_payment_and_method_for_yoo_money(self, mock_now):
        fixed_time = timezone.now()
        mock_now.return_value = fixed_time
        payload = deepcopy(self.base_payload)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(id=payload["object"]["id"])
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(payment.period_start, fixed_time)
        self.assertEqual(payment.amount, Decimal(payload["object"]["amount"]["value"]))
        self.assertEqual(
            payment.income_amount,
            Decimal(payload["object"]["income_amount"]["value"]),
        )
        method = PaymentMethod.objects.get(id=payload["object"]["payment_method"]["id"])
        self.assertEqual(method.user, self.user)
        self.assertEqual(method.status, PaymentMethodStatus.ACTIVE)
        self.assertEqual(
            method.details,
            {
                "type": "yoo_money",
                "number": payload["object"]["payment_method"]["account_number"],
            },
        )

    def test_webhook_logs_bank_card_payment_method_details(self):
        payload = deepcopy(self.base_payload)
        payload["object"]["payment_method"] = {
            "type": "bank_card",
            "id": "card_method",
            "card": {
                "first6": "411111",
                "last4": "1111",
                "expiry_year": "2028",
                "expiry_month": "09",
            },
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        method = PaymentMethod.objects.get(id="card_method")
        self.assertEqual(
            method.details,
            {
                "type": "bank_card",
                "number": "4111 11** **** 1111",
                "expire_date": "09/28",
            },
        )

    def test_webhook_updates_existing_payment_and_method(self):
        payload = deepcopy(self.base_payload)
        Payment.objects.create(
            id=payload["object"]["id"],
            user=self.user,
            status=PaymentStatus.UNPAID,
            period_start=timezone.now(),
            amount="10.00",
            income_amount="9.00",
        )
        PaymentMethod.objects.create(
            id=payload["object"]["payment_method"]["id"],
            user=self.user,
            status=PaymentMethodStatus.CANCELED,
            details={"type": "yoo_money", "number": "old"},
        )
        payload["object"]["amount"]["value"] = "250.00"
        payload["object"]["income_amount"]["value"] = "245.00"
        payload["object"]["payment_method"]["account_number"] = "410011000000000"

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_payment = Payment.objects.get(id=payload["object"]["id"])
        self.assertEqual(updated_payment.status, PaymentStatus.PAID)
        self.assertEqual(updated_payment.amount, Decimal("250.00"))
        self.assertEqual(updated_payment.income_amount, Decimal("245.00"))
        updated_method = PaymentMethod.objects.get(
            id=payload["object"]["payment_method"]["id"]
        )
        self.assertEqual(updated_method.status, PaymentMethodStatus.ACTIVE)
        self.assertEqual(
            updated_method.details,
            {"type": "yoo_money", "number": "410011000000000"},
        )
