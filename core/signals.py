from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Product

User = get_user_model()


@receiver(post_migrate, dispatch_uid="init_default_products")
def init_default_products(sender, **kwargs):
    if getattr(sender, "name", None) != "core":
        return
    for product in settings.DEFAULT_PRODUCTS:
        Product.objects.get_or_create(
            name=product["name"],
            defaults={
                "plan": product["plan"],
                "delay": product["delay"],
                "month_price": product["month_price"],
            },
        )
