from django.contrib.auth import get_user_model
from django.utils import timezone
from djstripe.models import Customer, PaymentMethod
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class PaymentMethodViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="method_user",
            email="method@example.com",
            password="method-password",
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/payments/method/"
        self.customer = self._create_customer()

    def _create_customer(self, customer_id="cus_method_user"):
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

    def _create_payment_method(self, method_id, last4=None):
        card_data = {"brand": "visa", "exp_month": 1, "exp_year": 2030}
        if last4:
            card_data["last4"] = last4
        stripe_data = {
            "id": method_id,
            "customer": self.customer.id,
            "type": "card",
            "card": card_data,
        }
        return PaymentMethod.objects.create(
            id=method_id,
            livemode=False,
            customer=self.customer,
            created=timezone.now(),
            metadata={},
            stripe_data=stripe_data,
        )

    def test_list_without_payment_methods(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_with_multiple_payment_methods(self):
        method_with_number = self._create_payment_method("pm_with_last4", last4="4242")
        method_without_number = self._create_payment_method("pm_without_last4")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            response.data,
            [
                {
                    "djstripe_id": method_with_number.djstripe_id,
                    "card_number": "**** **** **** 4242",
                },
                {
                    "djstripe_id": method_without_number.djstripe_id,
                    "card_number": "**** **** **** ****",
                },
            ],
        )
