from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from djstripe.models import Customer, Subscription
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from subscription_payments.api.serializers import SubscriptionSerializer
from subscription_payments.service import get_default_subscription_data

User = get_user_model()


class UserViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_view",
            email="user@example.com",
            password="view-password",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/users/"
        self.customer = None

    def _create_customer(self, customer_id="cus_user_view"):
        customer = Customer.objects.create(
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
        self.customer = customer
        return customer

    def _create_subscription(
        self,
        subscription_id,
        *,
        product_lookup_key="pro_month_subscription",
        created=None,
        status="active",
    ):
        if not self.customer:
            self._create_customer()
        created = created or timezone.now()
        stripe_data = {
            "id": subscription_id,
            "customer": self.customer.id,
            "status": status,
            "plan": product_lookup_key,
            "items": {
                "data": [
                    {
                        "id": f"si_{subscription_id}",
                        "price": {"lookup_key": product_lookup_key},
                        "quantity": 1,
                    }
                ]
            },
        }
        return Subscription.objects.create(
            id=subscription_id,
            livemode=False,
            customer=self.customer,
            created=created,
            metadata={},
            stripe_data=stripe_data,
        )

    def test_user_without_subscription_returns_default_data(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": self.user.id,
                "username": self.user.username,
                "subscription": get_default_subscription_data(),
            },
        )

    def test_user_with_single_subscription_returns_serialized_subscription(self):
        subscription = self._create_subscription("sub_single")
        expected_subscription = SubscriptionSerializer(subscription).data

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": self.user.id,
                "username": self.user.username,
                "subscription": expected_subscription,
            },
        )

    def test_user_with_multiple_subscriptions_returns_latest(self):
        older_created = timezone.now() - timedelta(days=5)
        self._create_subscription("sub_old", created=older_created)
        newest_subscription = self._create_subscription("sub_new")
        expected_subscription = SubscriptionSerializer(newest_subscription).data

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": self.user.id,
                "username": self.user.username,
                "subscription": expected_subscription,
            },
        )
