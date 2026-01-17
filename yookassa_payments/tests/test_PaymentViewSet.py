from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import PaymentStatus
from yookassa_payments.api.serializers import PaymentSerializer
from yookassa_payments.models import Payment

User = get_user_model()


class PaymentViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="yookassa_payment",
            email="yookassa_payment@example.com",
            password="strong-password-123",
        )
        self.other_user = User.objects.create_user(
            username="yookassa_payment_other",
            email="yookassa_payment_other@example.com",
            password="strong-password-123",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/yookassa/"

    def test_list_returns_only_user_payments(self):
        first_payment = Payment.objects.create(
            id="pay_user_1",
            user=self.user,
            status=PaymentStatus.PAID,
            period_start=timezone.now(),
            amount=Decimal("100.00"),
            income_amount=Decimal("95.00"),
        )
        second_payment = Payment.objects.create(
            id="pay_user_2",
            user=self.user,
            status=PaymentStatus.UNPAID,
            period_start=timezone.now(),
            amount=Decimal("200.00"),
            income_amount=Decimal("190.00"),
        )
        Payment.objects.create(
            id="pay_other",
            user=self.other_user,
            status=PaymentStatus.PAID,
            period_start=timezone.now(),
            amount=Decimal("50.00"),
            income_amount=Decimal("47.50"),
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            response.data,
            [
                PaymentSerializer(first_payment).data,
                PaymentSerializer(second_payment).data,
            ],
        )
