from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from core.models import Subscription
from .service import get_core_sub_from_djstripe_sub
import djstripe

User = get_user_model()


@receiver(post_save, sender=djstripe.models.Subscription)
def dublicate_user_subscription(sender, instance, created, **kwargs):
    if created:
        core_subscription = get_core_sub_from_djstripe_sub(instance)
        core_subscription.save()
