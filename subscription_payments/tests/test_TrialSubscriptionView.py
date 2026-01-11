from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from djstripe.models import Customer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


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
        self._create_customer()

    def _create_customer(self, customer_id="cus_trial_user"):
        Customer.objects.create(
            id=customer_id,
            livemode=False,
            subscriber=self.user,
            metadata={},
            stripe_data={
                "id": customer_id,
                "email": self.user.email,
                "name": self.user.username,
                "invoice_settings": {"default_payment_method": None},
            },
        )
        self.user.customer_id = customer_id
        self.user.save(update_fields=["customer_id"])

    @patch(
        "subscription_payments.api.views.TrialSubscriptionView.create_payment_session"
    )
    def test_trial_subscription_created(
        self,
        mock_create_payment_session,
    ):
        result = {
            "payment_session_link": "https://stripe.test/trial",
            "payment_session_id": "cs_test_trial",
        }
        mock_create_payment_session.return_value = Response(result)

        response = self.client.post(self.url, {})
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, result)
        mock_create_payment_session.assert_called_once()
        self.assertEqual(
            mock_create_payment_session.call_args.kwargs["trial_period_days"],
            settings.TRIAL_PERIOD_DAYS,
        )
        self.assertEqual(
            mock_create_payment_session.call_args.kwargs["product_name"],
            settings.TRIAL_PRODUCT_NAME,
        )

    def test_trial_subscription_forbidden_without_permission(self):
        self.user.may_have_trial = False
        self.user.save()

        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
