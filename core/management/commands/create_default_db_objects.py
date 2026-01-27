from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Product

User = get_user_model()


def create_default_products():
    for product in settings.DEFAULT_PRODUCTS:
        Product.objects.get_or_create(
            name=product["name"],
            defaults={
                "plan": product["plan"],
                "delay": product["delay"],
                "month_price": product["month_price"],
            },
        )


def create_default_super_user_if_debug():
    if not settings.DEBUG:
        return
    super_user = User.objects.filter(username=settings.DEBUG_ADMIN_NAME).first()
    if not super_user:
        return
    User.objects.create_superuser(
        username=settings.DEBUG_ADMIN_NAME,
        password=settings.DEBUG_ADMIN_PASSWORD,
    )


class Command(BaseCommand):

    def handle(self, *args, **options):
        create_default_products()
        create_default_super_user_if_debug()
        self.stdout.write("default objects created")
