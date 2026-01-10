from django.apps import AppConfig
from django.conf import settings


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscription_payments"

    def ready(self):
        import subscription_payments.signals
