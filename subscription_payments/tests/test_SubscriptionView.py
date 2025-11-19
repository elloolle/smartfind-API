from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from ..models import Subscription
from datetime import datetime, timedelta
import uuid

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

    def test_post_creates_subscription_session(self):

        response = self.client.post(
            self.url,
            {"product_name": "pro_month_subscription"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_subscription_already_exist(self):
        subscription = Subscription.objects.create(
            id=str(uuid.uuid4()),  # уникальный ID
            user=self.user,  # пользователь
            status="active",  # статус, один из choices
            month_price=9.99,  # цена подписки
            start_period=datetime.now(),  # дата начала подписки
            delay=timedelta(days=0),  # задержка, DurationField
            plan="pro",  # название плана
        )
        response = self.client.post(
            self.url,
            {"product_name": "pro_month_subscription"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
