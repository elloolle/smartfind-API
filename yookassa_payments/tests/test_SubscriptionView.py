from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class SubscriptionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="yookassa_user",
            email="yookassa@example.com",
            password="strong-password-123",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/yookassa/subscription/"

    @patch("yookassa_payments.api.views.get_subscription_payment_link")
    @override_settings(DEBUG=False)
    def test_post_creates_subscription_payment_link(
        self, mock_get_subscription_payment_link
    ):
        mock_get_subscription_payment_link.return_value = "https://pay.test/yookassa"
        product_name = f"{self.user.subscription.product_name}_upgrade"

        response = self.client.post(
            self.url, {"product_name": product_name}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, "https://pay.test/yookassa")
        mock_get_subscription_payment_link.assert_called_once_with(
            self.user.id, product_name
        )
