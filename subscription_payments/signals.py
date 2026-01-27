from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings

from core.models import Subscription as CoreSubscription, SubscriptionStatus
from .service import get_core_sub_dict_from_djstripe_sub
import djstripe

User = get_user_model()


@receiver(post_save, sender=djstripe.models.Subscription)
def dublicate_user_subscription(sender, instance, created, **kwargs):
    new_subscription = get_core_sub_dict_from_djstripe_sub(instance)
    old_subscription = CoreSubscription.objects.filter(
        user=new_subscription["user"]
    ).first()
    if old_subscription:
        old_subscription.delete()
    subscription = CoreSubscription(**new_subscription)
    subscription.save()
