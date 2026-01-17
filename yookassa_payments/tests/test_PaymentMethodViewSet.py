from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import PaymentMethodStatus
from yookassa_payments.api.serializers import PaymentMethodSerializer
from yookassa_payments.models import PaymentMethod

User = get_user_model()


class PaymentMethodViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="yookassa_method",
            email="yookassa_method@example.com",
            password="strong-password-123",
        )
        self.other_user = User.objects.create_user(
            username="yookassa_method_other",
            email="yookassa_method_other@example.com",
            password="strong-password-123",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/yookassa/method/"

    def test_list_returns_only_user_payment_methods(self):
        method = PaymentMethod.objects.create(
            id="pm_user",
            user=self.user,
            status=PaymentMethodStatus.ACTIVE,
            details={"type": "yoo_money", "number": "123"},
        )
        PaymentMethod.objects.create(
            id="pm_other",
            user=self.other_user,
            status=PaymentMethodStatus.ACTIVE,
            details={"type": "yoo_money", "number": "456"},
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [PaymentMethodSerializer(method).data])
