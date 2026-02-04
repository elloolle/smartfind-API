from django.contrib.auth import get_user_model
from djstripe.models import Customer, Subscription as DjstripeSubscription
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.api.serializers import SubscriptionSerializer
from core.models import Subscription, SubscriptionStatus
from users.api.serializers import UserSerializer
from datetime import datetime, timedelta

User = get_user_model()


class UserViewTests(APITestCase):
    def setUp(self):
        self.user = UserSerializer().create(
            {"username": "user_view", "password": "view-password"}
        )
        self.user.email = "user@example.com"
        self.user.save(update_fields=["email"])
        self.user.refresh_from_db()
        self.default_subscription = self.user.subscription
        self.default_subscription_id = self.default_subscription.id
        self.default_product_name = self.default_subscription.product.name
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/users/"
        self.customer = self._create_customer()

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
        return customer

    def _create_subscription(
        self,
        subscription_id,
        *,
        product_lookup_key="pro_month_subscription",
        subscription_status="active",
    ):
        start_date = datetime(year=2000, month=1, day=1)
        end_date = start_date + timedelta(days=30)
        stripe_data = {
            "id": subscription_id,
            "customer": self.customer.id,
            "status": subscription_status,
            "plan": product_lookup_key,
            "start_date": int(start_date.timestamp()),
            "ended_at": int(end_date.timestamp()),
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
        djstripe_subscription = DjstripeSubscription.objects.create(
            id=subscription_id,
            livemode=False,
            customer=self.customer,
            metadata={},
            stripe_data=stripe_data,
        )
        return djstripe_subscription

    def test_user_with_default_subscription_returns_serialized_subscription(self):
        expected_subscription = SubscriptionSerializer(self.default_subscription).data
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

    def test_active_djstripe_subscription_updates_user_subscription(self):
        subscription_id = "sub_active"
        product_lookup_key = "pro_month_subscription"
        self._create_subscription(
            subscription_id, product_lookup_key=product_lookup_key
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription.product.name, product_lookup_key)
        self.assertEqual(self.user.subscription.status, SubscriptionStatus.ACTIVE)
        expected_subscription = SubscriptionSerializer(self.user.subscription).data

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

    def test_updating_active_subscription_to_unpaid_updates_user_subscription(self):
        subscription_id = "sub_update_unpaid"
        djstripe_subscription = self._create_subscription(
            subscription_id, subscription_status="active"
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription.id, subscription_id)
        self.assertEqual(self.user.subscription.status, SubscriptionStatus.ACTIVE)

        djstripe_subscription.stripe_data["status"] = "unpaid"
        djstripe_subscription.save(update_fields=["stripe_data"])
        self.user.refresh_from_db()

        self.assertEqual(self.user.subscription.id, subscription_id)
        self.assertEqual(self.user.subscription.status, SubscriptionStatus.UNPAID)
        self.assertEqual(
            Subscription.objects.get(id=subscription_id).status,
            SubscriptionStatus.UNPAID,
        )
