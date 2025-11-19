import json
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from subscription_payments.models import Subscription

User = get_user_model()
event_data = {
    "api_version": "2025-10-29.clover",
    "created": 1763557116,
    "data": {
        "object": {
            "application": "null",
            "application_fee_percent": "null",
            "automatic_tax": {
                "disabled_reason": "null",
                "enabled": False,
                "liability": "null",
            },
            "billing_cycle_anchor": 1763557112,
            "billing_cycle_anchor_config": "null",
            "billing_mode": {
                "flexible": {"proration_discounts": "included"},
                "type": "flexible",
                "updated_at": 1763557095,
            },
            "billing_thresholds": "null",
            "cancel_at": "null",
            "cancel_at_period_end": False,
            "canceled_at": "null",
            "cancellation_details": {
                "comment": "null",
                "feedback": "null",
                "reason": "null",
            },
            "collection_method": "charge_automatically",
            "created": 1763557112,
            "currency": "usd",
            "customer": "cus_TRgdbk7xcFh4Dw",
            "days_until_due": "null",
            "default_payment_method": "pm_1SVAxwLlv1dDDiBEz60D1vCA",
            "default_source": "null",
            "default_tax_rates": [],
            "description": "null",
            "discounts": [],
            "ended_at": "null",
            "id": "sub_1SVAxzLlv1dDDiBERp446EVf",
            "invoice_settings": {"account_tax_ids": "null", "issuer": {"type": "self"}},
            "items": {
                "data": [
                    {
                        "billing_thresholds": "null",
                        "created": 1763557113,
                        "current_period_end": 1766149112,
                        "current_period_start": 1763557112,
                        "discounts": [],
                        "id": "si_TS58SeDCovR36I",
                        "metadata": {},
                        "object": "subscription_item",
                        "plan": {
                            "active": True,
                            "amount": 10000,
                            "amount_decimal": "10000",
                            "billing_scheme": "per_unit",
                            "created": 1763466755,
                            "currency": "usd",
                            "id": "price_1SUnSZLlv1dDDiBEv6FvUgaX",
                            "interval": "month",
                            "interval_count": 1,
                            "livemode": False,
                            "metadata": {},
                            "meter": "null",
                            "nickname": "null",
                            "object": "plan",
                            "product": "prod_TRgqxO6WGSb4rz",
                            "tiers_mode": "null",
                            "transform_usage": "null",
                            "trial_period_days": "null",
                            "usage_type": "licensed",
                        },
                        "price": {
                            "active": True,
                            "billing_scheme": "per_unit",
                            "created": 1763466755,
                            "currency": "usd",
                            "custom_unit_amount": "null",
                            "id": "price_1SUnSZLlv1dDDiBEv6FvUgaX",
                            "livemode": False,
                            "lookup_key": "pro_month_subscription",
                            "metadata": {},
                            "nickname": "null",
                            "object": "price",
                            "product": "prod_TRgqxO6WGSb4rz",
                            "recurring": {
                                "interval": "month",
                                "interval_count": 1,
                                "meter": "null",
                                "trial_period_days": "null",
                                "usage_type": "licensed",
                            },
                            "tax_behavior": "unspecified",
                            "tiers_mode": "null",
                            "transform_quantity": "null",
                            "type": "recurring",
                            "unit_amount": 10000,
                            "unit_amount_decimal": "10000",
                        },
                        "quantity": 1,
                        "subscription": "sub_1SVAxzLlv1dDDiBERp446EVf",
                        "tax_rates": [],
                    }
                ],
                "has_more": False,
                "object": "list",
                "total_count": 1,
                "url": "/v1/subscription_items?subscription=sub_1SVAxzLlv1dDDiBERp446EVf",
            },
            "latest_invoice": "in_1SVAxxLlv1dDDiBEHwMReQBy",
            "livemode": False,
            "metadata": {},
            "next_pending_invoice_item_invoice": "null",
            "object": "subscription",
            "on_behalf_of": "null",
            "pause_collection": "null",
            "payment_settings": {
                "payment_method_options": {
                    "acss_debit": "null",
                    "bancontact": "null",
                    "card": {"network": "null", "request_three_d_secure": "automatic"},
                    "customer_balance": "null",
                    "konbini": "null",
                    "sepa_debit": "null",
                    "us_bank_account": "null",
                },
                "payment_method_types": "null",
                "save_default_payment_method": "off",
            },
            "pending_invoice_item_interval": "null",
            "pending_setup_intent": "null",
            "pending_update": "null",
            "plan": {
                "active": True,
                "amount": 10000,
                "amount_decimal": "10000",
                "billing_scheme": "per_unit",
                "created": 1763466755,
                "currency": "usd",
                "id": "price_1SUnSZLlv1dDDiBEv6FvUgaX",
                "interval": "month",
                "interval_count": 1,
                "livemode": False,
                "metadata": {},
                "meter": "null",
                "nickname": "null",
                "object": "plan",
                "product": "prod_TRgqxO6WGSb4rz",
                "tiers_mode": "null",
                "transform_usage": "null",
                "trial_period_days": "null",
                "usage_type": "licensed",
            },
            "presentment_details": {"presentment_currency": "eur"},
            "quantity": 1,
            "schedule": "null",
            "start_date": 1763557112,
            "status": "active",
            "test_clock": "null",
            "transfer_data": "null",
            "trial_end": "null",
            "trial_settings": {
                "end_behavior": {"missing_payment_method": "create_invoice"}
            },
            "trial_start": "null",
        }
    },
    "id": "evt_1SVAy0Llv1dDDiBEAT8wepCy",
    "livemode": False,
    "object": "event",
    "pending_webhooks": 3,
    "request": {
        "id": "null",
        "idempotency_key": "5ba355d4-2fbe-4e31-8285-512f2d1ba6cb",
    },
    "type": "customer.subscription.created",
}


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
        mock_construct_event.return_value = event_data

        payload = json.dumps({"dummy": "data"})

        response = self.client.post(
            "/api/payments/webhook/",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        subscriptions = Subscription.objects.filter()
        self.assertEqual(subscriptions.count(), 1)
        subscription = subscriptions.first()
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
