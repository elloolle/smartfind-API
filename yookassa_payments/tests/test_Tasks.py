from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from core.helpers import now
from core.models import Product, Subscription, SubscriptionStatus
from yookassa_payments.tasks import update_subscriptions_statuses_based_on_end_period

User = get_user_model()


class YookassaTasksTests(APITestCase):
    def setUp(self):
        self._ensure_products()

    def _ensure_products(self):
        for product in settings.DEFAULT_PRODUCTS:
            Product.objects.get_or_create(
                name=product["name"],
                defaults={
                    "plan": product.get("plan"),
                    "month_price": product.get("month_price"),
                    "delay": product.get("delay"),
                },
            )

    def _create_user_with_subscription(self, username, product_name, end_period):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="strong-password-123",
        )
        user.subscription.delete()
        product = Product.objects.get(name=product_name)
        return Subscription.objects.create(
            user=user,
            status=SubscriptionStatus.ACTIVE,
            product=product,
            end_period=end_period,
        )

    def test_update_subscriptions_statuses_based_on_end_period(self):
        expired_end = now() - timedelta(days=1)
        future_end = now() + timedelta(days=1)
        expired_trial = self._create_user_with_subscription(
            "expired_trial_user", settings.TRIAL_PRODUCT_NAME, expired_end
        )
        expired_pro = self._create_user_with_subscription(
            "expired_pro_user", "pro_month_subscription", expired_end
        )
        expired_default = self._create_user_with_subscription(
            "expired_default_user", settings.DEFAULT_PRODUCT_NAME, expired_end
        )
        active_trial = self._create_user_with_subscription(
            "active_trial_user", settings.TRIAL_PRODUCT_NAME, future_end
        )
        active_pro = self._create_user_with_subscription(
            "active_pro_user", "pro_month_subscription", future_end
        )
        active_default = self._create_user_with_subscription(
            "active_default_user", settings.DEFAULT_PRODUCT_NAME, future_end
        )

        update_subscriptions_statuses_based_on_end_period()

        for subscription in (expired_trial, expired_pro, expired_default):
            subscription.refresh_from_db()
            self.assertEqual(subscription.status, SubscriptionStatus.UNPAID)
        for subscription in (active_trial, active_pro, active_default):
            subscription.refresh_from_db()
            self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
