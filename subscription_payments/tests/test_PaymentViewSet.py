from datetime import datetime, timezone as dt_timezone, UTC

from django.contrib.auth import get_user_model
from django.utils import timezone
from djstripe.models import Customer, Invoice
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class PaymentViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payment_user",
            email="payment@example.com",
            password="payment-password",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/payments/"
        self.customer = self._create_customer()

    def _create_customer(self, customer_id="cus_payment_user"):
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

    def _create_invoice(self, invoice_id, amount, period_start, invoice_status="paid"):
        stripe_data = {
            "id": invoice_id,
            "customer": self.customer.id,
            "status": invoice_status,
            "period_start": period_start,
            "amount_due": amount,
        }
        return Invoice.objects.create(
            id=invoice_id,
            livemode=False,
            customer=self.customer,
            created=timezone.now(),
            metadata={},
            stripe_data=stripe_data,
        )

    def test_list_without_invoices(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_with_invoices(self):
        first_period_start = int(
            datetime(2025, 1, 1, tzinfo=UTC).timestamp()
        )
        second_period_start = int(
            datetime(2025, 2, 1, tzinfo=UTC).timestamp()
        )
        first_invoice = self._create_invoice(
            "inv_first",
            amount=5000,
            period_start=first_period_start,
            invoice_status="paid",
        )
        second_invoice = self._create_invoice(
            "inv_second",
            amount=1234,
            period_start=second_period_start,
            invoice_status="draft",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            response.data,
            [
                {
                    "djstripe_id": first_invoice.djstripe_id,
                    "status": "paid",
                    "period_start": datetime.utcfromtimestamp(first_period_start),
                    "amount": 50.0,
                },
                {
                    "djstripe_id": second_invoice.djstripe_id,
                    "status": "draft",
                    "period_start": datetime.utcfromtimestamp(second_period_start),
                    "amount": 12.34,
                },
            ],
        )
