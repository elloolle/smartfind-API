from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class TrialFlag:
    def __init__(self, value=True):
        self.value = value

    def __bool__(self):
        return self.value

    def set(self, value):
        self.value = value


class TrialSubscriptionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="trial_user",
            email="trial@example.com",
            password="trial-password",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/payments/set_trial/"

    @patch("subscription_payments.api.views.TrialSubscriptionView.create_payment_link")
    def test_trial_subscription_created(
        self,
        mock_create_payment_link,
    ):
        self.user.may_have_trial = True
        result = {"checkout_url": "https://stripe.test/trial"}
        mock_create_payment_link.return_value = Response(result)

        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, result)
        self.assertFalse(self.user.may_have_trial)
        self.assertEqual(
            mock_create_payment_link.call_args.kwargs["trial_period_days"],
            settings.TRIAL_PERIOD_DAYS,
        )

    def test_trial_subscription_forbidden_without_permission(self):
        self.user.may_have_trial = False
        self.user.save()

        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"status": "user does not have trial permissions"}
        )
