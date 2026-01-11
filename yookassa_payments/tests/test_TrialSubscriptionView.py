from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class TrialSubscriptionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="yookassa_trial",
            email="yookassa_trial@example.com",
            password="strong-password-123",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/yookassa/set_trial/"

    @patch("yookassa_payments.api.views.get_trial_subscription_payment_link")
    def test_post_creates_trial_subscription_payment_link(
        self, mock_get_trial_subscription_payment_link
    ):
        mock_get_trial_subscription_payment_link.return_value = (
            "https://pay.test/yookassa-trial"
        )

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, "https://pay.test/yookassa-trial")
        mock_get_trial_subscription_payment_link.assert_called_once_with(
            self.user.id, settings.TRIAL_PRODUCT_NAME
        )
