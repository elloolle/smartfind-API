from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class GetEmbeddingsViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="portal_user",
            email="portal@example.com",
            password="portal-password",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/payments/portal_link/"

    @patch("stripe.billing_portal.Session.create")
    def test_portal_link_created_for_customer(self, mock_session_create):
        self.user.customer_id = "cus_123"
        self.user.save()
        mock_session_create.return_value = SimpleNamespace(
            url="https://portal.stripe.test"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"portal_session_link": "https://portal.stripe.test"}
        )
        mock_session_create.assert_called_once_with(
            customer="cus_123", return_url=settings.SUCCESS_URL
        )
