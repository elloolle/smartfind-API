from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from djstripe.models import Customer, Subscription

from core.models import Product, Subscription as CoreSubscription, SubscriptionStatus

User = get_user_model()


class SubscriptionSignalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_user",
            email="test@example.com",
            password="strong-password-123",
        )
        self.product = Product.objects.get(
            name="pro_month_subscription",
        )
        self.customer = Customer.objects.create(
            id="cus_test_user",
            livemode=False,
            subscriber=self.user,
            metadata={},
            stripe_data={
                "id": "cus_test_user",
                "email": self.user.email,
                "name": self.user.username,
                "invoice_settings": {"default_payment_method": None},
            },
        )
        self.user.customer_id = self.customer.id
        self.user.save(update_fields=["customer_id"])

    def _create_subscription(self, *, subscription_id="sub_test", status="active"):
        start_date = datetime(year=2000, month=1, day=1)
        end_date = start_date + timedelta(days=30)
        stripe_data = {
            "id": subscription_id,
            "customer": self.customer.id,
            "status": status,
            "plan": self.product.name,
            "start_date": int(start_date.timestamp()),
            "ended_at": int(end_date.timestamp()),
            "items": {
                "data": [
                    {
                        "id": f"si_{subscription_id}",
                        "price": {"lookup_key": self.product.name},
                        "quantity": 1,
                    }
                ]
            },
        }
        subscription = Subscription.objects.create(
            id=subscription_id,
            livemode=False,
            customer=self.customer,
            metadata={},
            stripe_data=stripe_data,
        )
        return subscription, start_date, end_date

    def test_subscription_post_save_creates_core_subscription(self):
        subscription, start_date, end_date = self._create_subscription()

        core_subscription = CoreSubscription.objects.get(id=subscription.id)
        self.assertEqual(core_subscription.user, self.user)
        self.assertEqual(core_subscription.product, self.product)
        self.assertEqual(core_subscription.status, SubscriptionStatus.ACTIVE)
        expected_start = timezone.make_aware(start_date)
        expected_end = timezone.make_aware(end_date)
        self.assertEqual(core_subscription.start_period, expected_start)
        self.assertEqual(core_subscription.end_period, expected_end)
