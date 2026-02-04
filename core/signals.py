from django.db.models.signals import post_migrate, post_save
from django.conf import settings
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from core.service import create_default_subscription_to_user
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
    if super_user:
        return
    User.objects.create_superuser(
        username=settings.DEBUG_ADMIN_NAME,
        password=settings.DEBUG_ADMIN_PASSWORD,
    )


@receiver(post_migrate)
def init_default_data_into_db(sender, **kwargs):
    create_default_products()
    create_default_super_user_if_debug()


@receiver(post_save, sender=User)
def add_default_subscription(sender, instance, created, **kwargs):
    if created and not getattr(instance, "subscription", None):
        create_default_subscription_to_user(instance)
