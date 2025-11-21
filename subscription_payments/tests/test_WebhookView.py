import json
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from .webhook_test_events import (
    charge_failed,
    customer_subscription_created,
    invoice_payment_succeeded,
    payment_intent_payment_failed,
)
from subscription_payments.models import Payment, PaymentStatus, Subscription

User = get_user_model()


class StripeWebhookTests(APITestCase):
    def setUp(self):
        # Создаём пользователя с нужным customer_id прямо в тестовой базе
        self.user = User.objects.create(
            username="testuser",
            email="test@test.com",
            customer_id="cus_TRgdbk7xcFh4Dw",
        )

    @patch("stripe.Webhook.construct_event")
    def test_payment_intent_succeeded(self, mock_construct_event):
        event_data = customer_subscription_created
        mock_construct_event.return_value = event_data

        payload = json.dumps({"dummy": "data"})

        response = self.client.post(
            "/api/payments/webhook/",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        subscriptions = Subscription.objects.filter()
        self.assertEqual(subscriptions.count(), 2)
        subscription = subscriptions[1]
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.id, event_data["data"]["object"]["id"])
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.status, event_data["data"]["object"]["status"])

        product_name = event_data["data"]["object"]["items"]["data"][0]["price"][
            "lookup_key"
        ]
        product_config = settings.PRODUCTS[product_name]
        self.assertEqual(subscription.month_price, product_config["month_price"])
        self.assertEqual(subscription.delay, product_config["delay"])
        self.assertEqual(subscription.plan, product_config["plan"])

        delta = timezone.now() - subscription.start_period
        self.assertLess(delta, timedelta(seconds=5))

    # @patch("stripe.Webhook.construct_event")
    # def test_payment_intent_payment_failed_creates_pending_payment(
    #     self, mock_construct_event
    # ):
    #     mock_construct_event.return_value = {
    #         "type": "payment_intent.payment_failed",
    #         "data": {"object": payment_intent_payment_failed},
    #     }
    #
    #     payload = json.dumps({"dummy": "data"})
    #
    #     response = self.client.post(
    #         "/api/payments/webhook/",
    #         data=payload,
    #         content_type="application/json",
    #     )
    #
    #     self.assertEqual(response.status_code, 200)
    #     payments = Payment.objects.filter()
    #     self.assertEqual(payments.count(), 1)
    #     payment = payments.first()
    #     self.assertIsNotNone(payment)
    #     self.assertEqual(payment.id, payment_intent_payment_failed["id"])
    #     self.assertEqual(payment.user, self.user)
    #     self.assertEqual(payment.type, "payment_intent")
    #     self.assertEqual(payment.status, PaymentStatus.pending)
    #
    # @patch("stripe.Webhook.construct_event")
    # def test_invoice_payment_succeeded_creates_succeeded_payment(
    #     self, mock_construct_event
    # ):
    #     mock_construct_event.return_value = {
    #         "type": "invoice.payment_succeeded",
    #         "data": {"object": invoice_payment_succeeded},
    #     }
    #
    #     payload = json.dumps({"dummy": "data"})
    #
    #     response = self.client.post(
    #         "/api/payments/webhook/",
    #         data=payload,
    #         content_type="application/json",
    #     )
    #
    #     self.assertEqual(response.status_code, 200)
    #     payments = Payment.objects.filter()
    #     self.assertEqual(payments.count(), 1)
    #     payment = payments.first()
    #     self.assertIsNotNone(payment)
    #     self.assertEqual(payment.id, invoice_payment_succeeded["id"])
    #     self.assertEqual(payment.user, self.user)
    #     self.assertEqual(payment.type, "invoice")
    #     self.assertEqual(payment.status, PaymentStatus.succeeded)
    #
    # @patch("stripe.Webhook.construct_event")
    # def test_charge_failed_creates_failed_payment(self, mock_construct_event):
    #     mock_construct_event.return_value = {
    #         "type": "charge.failed",
    #         "data": {"object": charge_failed},
    #     }
    #
    #     payload = json.dumps({"dummy": "data"})
    #
    #     response = self.client.post(
    #         "/api/payments/webhook/",
    #         data=payload,
    #         content_type="application/json",
    #     )
    #
    #     self.assertEqual(response.status_code, 200)
    #     payments = Payment.objects.filter()
    #     self.assertEqual(payments.count(), 1)
    #     payment = payments.first()
    #     self.assertIsNotNone(payment)
    #     self.assertEqual(payment.id, charge_failed["id"])
    #     self.assertEqual(payment.user, self.user)
    #     self.assertEqual(payment.type, "charge")
    #     self.assertEqual(payment.status, PaymentStatus.failed)
