import uuid

from django.conf import settings
from loguru import logger
from core.models import SubscriptionStatus, Subscription, Product


def create_default_subscription_to_user(user):
    default_product = Product.objects.get(name=settings.DEFAULT_PRODUCT_NAME)
    return Subscription.objects.create(
        id=uuid.uuid4(),
        user=user,
        status=SubscriptionStatus.ACTIVE,
        product=default_product,
    )
