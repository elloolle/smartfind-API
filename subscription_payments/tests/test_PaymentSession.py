from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class PaymentSessionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payment_session_user",
            email="payment_session@example.com",
            password="payment-session-password",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.payment_session_id = "cs_test_session"
        self.url = f"/api/payments/session/{self.payment_session_id}/"

    @patch("stripe.checkout.Session.retrieve")
    def test_get_payment_session_not_found(self, mock_session_retrieve):
        mock_session_retrieve.side_effect = Exception("not found")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_session_retrieve.assert_called_once_with(id=self.payment_session_id)

    @patch("stripe.checkout.Session.retrieve")
    def test_get_payment_session_exists(self, mock_session_retrieve):
        mock_session_retrieve.return_value = SimpleNamespace(status="complete")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_session_retrieve.assert_called_once_with(id=self.payment_session_id)
