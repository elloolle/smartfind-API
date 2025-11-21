from datetime import timedelta
import uuid
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import override_settings
from ..models import Subscription, SubscriptionStatus

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

    def create_trial_subscription(self):
        return self._create_subscription(
            status=SubscriptionStatus.trialing,
            plan="trial",
            start_offset=-2,
        )

    def create_canceled_subscription(self):
        return self._create_subscription(
            status=SubscriptionStatus.canceled,
            plan="basic",
            start_offset=-1,
        )

    def create_active_subscription(self):
        return self._create_subscription(
            status=SubscriptionStatus.active,
            plan="pro",
            start_offset=0,
        )

    def _create_subscription(self, *, status, plan, start_offset):
        return Subscription.objects.create(
            id=str(uuid.uuid4()),
            user=self.user,
            status=status,
            month_price=100,
            start_period=timezone.now() + timedelta(days=start_offset),
            delay=timedelta(days=30),
            plan=plan,
        )

    @patch("subscription_payments.api.views.SubscriptionView.create_payment_link")
    def test_post_creates_subscription_session(self, mock_create_payment_link):
        checkout_url = "https://stripe.test/checkout"
        mock_create_payment_link.return_value = Response(
            data={"checkout_url": checkout_url},
            status=status.HTTP_200_OK,
        )

        response = self.client.post(
            self.url,
            {"product_name": "pro_month_subscription"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"checkout_url": checkout_url})
        mock_create_payment_link.assert_called_once_with("pro_month_subscription")

    @override_settings(IGNORE_CLONE_SUBSCRIPTIONS=False)
    @patch("subscription_payments.api.views.get_subscription_plan_from_product_name")
    def test_post_subscription_already_exist(self, mock_get_subscription_plan):
        self.create_trial_subscription()
        self.create_canceled_subscription()
        self.create_active_subscription()
        mock_get_subscription_plan.return_value = "pro"

        response = self.client.post(
            self.url,
            {"product_name": "pro_month_subscription"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_when_user_not_subscribed(self):
        self.create_trial_subscription()
        self.create_canceled_subscription()
        self.create_active_subscription()

        unsubscribed_user = User.objects.create_user(
            username="no_sub_user",
            email="no_sub@example.com",
            password="no-sub-password",
        )
        token = str(RefreshToken.for_user(unsubscribed_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch("stripe.Subscription.modify")
    def test_delete_when_user_has_subscription(self, mock_modify_subscription):
        self.create_trial_subscription()
        self.create_canceled_subscription()
        active_subscription = self.create_active_subscription()

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_modify_subscription.assert_called_once_with(
            active_subscription.id,
            metadata={
                "collection_method": "send_invoice",
                "days_until_due": settings.DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION,
            },
        )
