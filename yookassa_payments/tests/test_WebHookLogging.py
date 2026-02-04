from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import PaymentMethodStatus, PaymentStatus, Product, SubscriptionStatus
from yookassa_payments.models import Payment, PaymentMethod
from .webhooks import (
    copy_payload,
    payment_canceled_bank_card,
    payment_succeeded,
    trial_payment_succeeded,
)

User = get_user_model()


class WebHookLoggingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="yookassa_logging",
            email="yookassa_logging@example.com",
            password="strong-password-123",
        )
        self._ensure_products()
        self.url = "/api/yookassa/webhook/"
        self.base_payload = payment_succeeded(self.user.id)
        self.base_payload["object"]["id"] = "log-payment-id"
        self.base_payload["object"]["payment_method"]["id"] = "log-method-id"

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

    def test_logs_payment_and_method_for_failed_auto_pay(self):
        payload = copy_payload(self.base_payload)
        payload["event"] = "payment.canceled"
        payload["object"]["status"] = "canceled"
        payload["object"]["paid"] = False
        payload["object"]["metadata"]["auto_pay"] = True

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(id=payload["object"]["id"])
        self.assertEqual(payment.status, PaymentStatus.UNPAID)
        self.assertEqual(payment.amount, Decimal("100.00"))
        method = PaymentMethod.objects.get(id=payload["object"]["payment_method"]["id"])
        self.assertEqual(method.status, PaymentMethodStatus.CANCELED)
        self.assertEqual(
            method.details,
            {
                "type": "yoo_money",
                "number": payload["object"]["payment_method"]["account_number"],
            },
        )

    def test_logs_payment_and_method_for_canceled_bank_card_payment(self):
        payload = payment_canceled_bank_card(self.user.id)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(id=payload["object"]["id"])
        self.assertEqual(payment.status, PaymentStatus.UNPAID)
        method = PaymentMethod.objects.get(id=payload["object"]["payment_method"]["id"])
        self.assertEqual(method.status, PaymentMethodStatus.CANCELED)
        self.assertEqual(
            method.details,
            {
                "type": "bank_card",
                "number": "2200 00** **** 0079",
                "expire_date": "11/30",
            },
        )

    def test_logs_payment_and_method_for_successful_trial_payment(self):
        payload = trial_payment_succeeded(self.user.id)
        payload["object"]["id"] = "log-trial-payment-id"
        payload["object"]["payment_method"]["id"] = "log-trial-method-id"

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(id=payload["object"]["id"])
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(payment.amount, Decimal("100.00"))
        self.assertEqual(
            PaymentMethod.objects.get(id=payload["object"]["payment_method"]["id"]).status,
            PaymentMethodStatus.ACTIVE,
        )

    def test_logs_bank_card_payment_method_on_success(self):
        payload = copy_payload(self.base_payload)
        payload["object"]["payment_method"] = {
            "type": "bank_card",
            "id": "log-card-id",
            "card": {
                "first6": "411111",
                "last4": "1111",
                "expiry_year": "2028",
                "expiry_month": "09",
            },
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        method = PaymentMethod.objects.get(id="log-card-id")
        self.assertEqual(method.status, PaymentMethodStatus.ACTIVE)
        self.assertEqual(
            method.details,
            {
                "type": "bank_card",
                "number": "4111 11** **** 1111",
                "expire_date": "09/28",
            },
        )
