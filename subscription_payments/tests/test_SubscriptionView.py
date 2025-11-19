from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
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

    @patch("subscription_payments.api.views.get_subscription_plan_from_product_name")
    @patch("subscription_payments.api.views.get_last_user_subscription")
    def test_post_subscription_already_exist(
        self,
        mock_get_last_user_subscription,
        mock_get_subscription_plan,
    ):
        mock_get_last_user_subscription.return_value = SimpleNamespace(plan="pro")
        mock_get_subscription_plan.return_value = "pro"

        response = self.client.post(
            self.url,
            {"product_name": "pro_month_subscription"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            response.data, {"error": "user already subscribed for this plan"}
        )

    @patch("subscription_payments.api.views.get_last_user_subscription")
    def test_delete_when_user_not_subscribed(self, mock_get_last_user_subscription):
        mock_get_last_user_subscription.return_value = None

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data, {"error": "user aren't subscribed"})

    @patch("stripe.Subscription.modify")
    @patch("subscription_payments.api.views.get_last_user_subscription")
    def test_delete_when_user_has_subscription(
        self,
        mock_get_last_user_subscription,
        mock_modify_subscription,
    ):
        mock_get_last_user_subscription.return_value = SimpleNamespace(id="sub_123")

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "success"})
        mock_modify_subscription.assert_called_once_with(
            "sub_123",
            metadata={
                "collection_method": "send_invoice",
                "days_until_due": settings.DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION,
            },
        )
