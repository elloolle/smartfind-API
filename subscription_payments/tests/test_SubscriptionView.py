from datetime import datetime, timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from djstripe.models import Customer, Subscription
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class SubscriptionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_user",
            email="test@example.com",
            password="strong-password-123",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/payments/subscription/"
        self.customer = self._create_customer()

    def _create_customer(self, customer_id="cus_test_user"):
        customer = Customer.objects.create(
            id=customer_id,
            livemode=False,
            subscriber=self.user,
            metadata={},
            stripe_data={
                "id": customer_id,
                "email": self.user.email,
                "name": self.user.username,
                "invoice_settings": {"default_payment_method": None},
            },
        )
        self.user.customer_id = customer_id
        self.user.save(update_fields=["customer_id"])
        return customer

    def _create_subscription(
        self,
        *,
        subscription_id="sub_test",
        product_lookup_key="pro_month_subscription",
        subscription_status="active",
    ):
        start_date = datetime(year=2000, month=1, day=1)
        end_date = start_date + timedelta(days=30)
        stripe_data = {
            "id": subscription_id,
            "customer": self.customer.id,
            "status": subscription_status,
            "plan": product_lookup_key,
            "start_date": int(start_date.timestamp()),
            "ended_at": int(end_date.timestamp()),
            "items": {
                "data": [
                    {
                        "id": f"si_{subscription_id}",
                        "price": {"lookup_key": product_lookup_key},
                        "quantity": 1,
                    }
                ]
            },
        }
        return Subscription.objects.create(
            id=subscription_id,
            livemode=False,
            customer=self.customer,
            metadata={},
            stripe_data=stripe_data,
        )

    @patch("subscription_payments.api.views.SubscriptionView.create_payment_session")
    def test_post_creates_subscription_session(self, mock_create_payment_session):
        result = {
            "payment_session_link": "https://stripe.test/checkout",
            "payment_session_id": "cs_test_checkout",
        }
        mock_create_payment_session.return_value = Response(result)

        response = self.client.post(
            self.url,
            {"product_name": "pro_month_subscription"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, result)
        mock_create_payment_session.assert_called_once_with("pro_month_subscription")

    @override_settings(IGNORE_CLONE_SUBSCRIPTIONS=False)
    def test_post_subscription_already_exist(self):
        self._create_subscription(product_lookup_key="pro_month_subscription")

        response = self.client.post(
            self.url,
            {"product_name": "pro_month_subscription"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_when_user_not_subscribed(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("stripe.Subscription.modify")
    def test_delete_when_user_has_subscription(self, mock_modify_subscription):
        subscription = self._create_subscription(subscription_id="sub_active")

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_modify_subscription.assert_called_once_with(
            subscription.id,
            collection_method="send_invoice",
            days_until_due=settings.DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION,
        )
