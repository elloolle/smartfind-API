import json
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    PaymentMethodStatus,
    PaymentStatus,
    Product,
    Subscription,
    SubscriptionStatus,
)
from yookassa_payments.models import Payment, PaymentMethod
from .webhooks import (
    copy_payload,
    payment_canceled_bank_card,
    payment_method_active_bank_card,
    payment_succeeded,
    payment_succeeded_bank_card,
    trial_payment_succeeded,
)
from ..service import AUTO_PAY_JOB_NAME, PAY_ONCE_JOB_NAME

User = get_user_model()


class WebHookViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="yookassa_webhook",
            email="yookassa_webhook@example.com",
            password="strong-password-123",
        )
        self._ensure_products()
        self.url = "/api/yookassa/webhook/"
        self.base_payload = payment_succeeded(self.user.id)

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

    def _assert_auto_pay_task(self, payment_method_id, amount, user_id, product_name):
        task = PeriodicTask.objects.get(name=f"{AUTO_PAY_JOB_NAME}_{payment_method_id}")
        self.assertEqual(task.task, "yookassa_payments.tasks.withdraw_money")
        kwargs = json.loads(task.kwargs)
        self.assertEqual(kwargs["payment_method_id"], payment_method_id)
        self.assertEqual(kwargs["amount"], amount)
        self.assertEqual(
            kwargs["metadata"],
            {
                "user_id": user_id,
                "product": product_name,
                "auto_pay": True,
                "trial": False,
            },
        )

    def _assert_pay_once_task(self, payment_method_id, amount, user_id, product_name):
        task = PeriodicTask.objects.get(name=f"{PAY_ONCE_JOB_NAME}_{payment_method_id}")
        self.assertEqual(task.task, "yookassa_payments.tasks.withdraw_money")
        kwargs = json.loads(task.kwargs)
        self.assertEqual(kwargs["payment_method_id"], payment_method_id)
        self.assertEqual(kwargs["amount"], amount)
        self.assertEqual(
            kwargs["metadata"],
            {
                "user_id": user_id,
                "product": product_name,
                "auto_pay": False,
                "trial": False,
            },
        )

    def test_webhook_payment_succeeded_creates_subscription_and_task(self):
        payload = copy_payload(self.base_payload)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.product.name, "pro_month_subscription")
        self._assert_auto_pay_task(
            payment_method_id=payload["object"]["payment_method"]["id"],
            amount=subscription.product.month_price,
            user_id=self.user.id,
            product_name=subscription.product.name,
        )
        interval = IntervalSchedule.objects.get(
            every=settings.DAYS_IN_MONTH, period=IntervalSchedule.DAYS
        )
        self.assertEqual(
            PeriodicTask.objects.get(
                name=f"{AUTO_PAY_JOB_NAME}_{payload['object']['payment_method']['id']}"
            ).interval_id,
            interval.id,
        )

    def test_webhook_trial_payment_succeeded_creates_subscription_and_task(self):
        payload = trial_payment_succeeded(self.user.id)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.product.name, settings.TRIAL_PRODUCT_NAME)
        self._assert_auto_pay_task(
            payment_method_id=payload["object"]["payment_method"]["id"],
            amount=subscription.product.month_price,
            user_id=self.user.id,
            product_name=subscription.product.name,
        )
        interval = IntervalSchedule.objects.get(
            every=settings.DAYS_IN_MONTH, period=IntervalSchedule.DAYS
        )
        self.assertEqual(
            PeriodicTask.objects.get(
                name=f"{AUTO_PAY_JOB_NAME}_{payload['object']['payment_method']['id']}"
            ).interval_id,
            interval.id,
        )

    def test_webhook_payment_canceled_marks_subscription_unpaid_and_removes_task(self):
        payment_method_id = self.base_payload["object"]["payment_method"]["id"]
        product = Product.objects.get(name="pro_month_subscription")
        self.user.subscription.delete()
        subscription = Subscription.objects.create(
            user=self.user,
            status=SubscriptionStatus.ACTIVE,
            product=product,
        )
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=settings.DAYS_IN_MONTH, period=IntervalSchedule.DAYS
        )
        PeriodicTask.objects.create(
            name=f"{AUTO_PAY_JOB_NAME}_{payment_method_id}",
            interval=interval,
            task="yookassa_payments.tasks.withdraw_money",
            start_time=timezone.now(),
            enabled=True,
            kwargs=json.dumps(
                {"payment_method_id": payment_method_id, "product_id": product.pk},
                sort_keys=True,
            ),
        )
        payload = copy_payload(self.base_payload)
        payload["event"] = "payment.canceled"

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertTrue(
            PeriodicTask.objects.filter(
                name=f"{AUTO_PAY_JOB_NAME}_{payment_method_id}"
            ).exists()
        )

    def test_webhook_logs_payment_and_method_for_yoo_money(self):
        payload = copy_payload(self.base_payload)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(id=payload["object"]["id"])
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(payment.amount, Decimal(payload["object"]["amount"]["value"]))
        self.assertEqual(
            payment.income_amount,
            Decimal(payload["object"]["income_amount"]["value"]),
        )
        method = PaymentMethod.objects.get(id=payload["object"]["payment_method"]["id"])
        self.assertEqual(method.user, self.user)
        self.assertEqual(method.status, PaymentMethodStatus.ACTIVE)
        self.assertEqual(
            method.details,
            {
                "type": "yoo_money",
                "number": payload["object"]["payment_method"]["account_number"],
            },
        )

    def test_webhook_logs_bank_card_payment_method_details(self):
        payload = payment_succeeded_bank_card(self.user.id)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        method = PaymentMethod.objects.get(id=payload["object"]["payment_method"]["id"])
        self.assertEqual(
            method.details,
            {
                "type": "bank_card",
                "number": "4111 11** **** 1111",
                "expire_date": "09/28",
            },
        )

    def test_webhook_updates_existing_payment_and_method(self):
        payload = copy_payload(self.base_payload)
        Payment.objects.create(
            id=payload["object"]["id"],
            user=self.user,
            status=PaymentStatus.UNPAID,
            period_start=timezone.now(),
            amount="10.00",
            income_amount="9.00",
        )
        PaymentMethod.objects.create(
            id=payload["object"]["payment_method"]["id"],
            user=self.user,
            status=PaymentMethodStatus.CANCELED,
            details={"type": "yoo_money", "number": "old"},
        )
        payload["object"]["amount"]["value"] = "250.00"
        payload["object"]["income_amount"]["value"] = "245.00"
        payload["object"]["payment_method"]["account_number"] = "410011000000000"

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_payment = Payment.objects.get(id=payload["object"]["id"])
        self.assertEqual(updated_payment.status, PaymentStatus.PAID)
        self.assertEqual(updated_payment.amount, Decimal("250.00"))
        self.assertEqual(updated_payment.income_amount, Decimal("245.00"))
        updated_method = PaymentMethod.objects.get(
            id=payload["object"]["payment_method"]["id"]
        )
        self.assertEqual(updated_method.status, PaymentMethodStatus.ACTIVE)
        self.assertEqual(
            updated_method.details,
            {"type": "yoo_money", "number": "410011000000000"},
        )

    def test_webhook_payment_canceled_first_payment_keeps_subscription_and_skips_method(
        self,
    ):
        payload = payment_canceled_bank_card(self.user.id)
        existing_subscription = Subscription.objects.get(user=self.user)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Subscription.objects.filter(id=existing_subscription.id).exists()
        )
        self.assertEqual(
            Subscription.objects.get(id=existing_subscription.id).status,
            existing_subscription.status,
        )
        self.assertFalse(
            PaymentMethod.objects.filter(
                id=payload["object"]["payment_method"]["id"]
            ).exists()
        )

    def test_webhook_payment_method_active_trial_creates_once_task_and_disables_trial(
        self,
    ):
        payment_method_id = "3115828b-0037-5000-8000-0c64f3fdb5c0"
        PaymentMethod.objects.create(
            id=payment_method_id,
            user=self.user,
            status=PaymentMethodStatus.PENDING,
            details={},
        )
        self.user.may_have_trial = True
        self.user.save(update_fields=["may_have_trial"])
        self.user.subscription.delete()
        payload = payment_method_active_bank_card(payment_method_id)

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.product.name, settings.TRIAL_PRODUCT_NAME)
        task = PeriodicTask.objects.get(name=f"{PAY_ONCE_JOB_NAME}_{payment_method_id}")
        self.assertTrue(task.one_off)
        self.assertEqual(task.task, "yookassa_payments.tasks.withdraw_money")
        kwargs = json.loads(task.kwargs)
        self.assertEqual(kwargs["payment_method_id"], payment_method_id)
        self.assertEqual(kwargs["amount"], subscription.product.month_price)
        self.assertEqual(
            kwargs["metadata"],
            {
                "user_id": self.user.id,
                "product": subscription.product.name,
                "auto_pay": False,
                "trial": False,
            },
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.may_have_trial)
