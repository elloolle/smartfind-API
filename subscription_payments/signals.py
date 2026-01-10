from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings

from core.models import Subscription, SubscriptionStatus
from .service import get_core_sub_from_djstripe_sub
import djstripe

User = get_user_model()


@receiver(post_save, sender=djstripe.models.Subscription)
def dublicate_user_subscription(sender, instance, created, **kwargs):
    core_subscription = get_core_sub_from_djstripe_sub(instance)
    if core_subscription.status == SubscriptionStatus.ACTIVE:
        user.subscription = core_subscription


@receiver(
    post_migrate, dispatch_uid="subscription_payments_set_djstripe_webhook_secret"
)
def set_djstripe_webhook_secret(sender, **kwargs):
    if getattr(sender, "name", None) != "djstripe":
        return
    raw = getattr(settings, "DJSTRIPE_WEBHOOK_SECRET", "")
    if not raw:
        return
    try:
        from djstripe.models import WebhookEndpoint

        endpoint = WebhookEndpoint.objects.first()
    except Exception:
        return
    if not endpoint:
        return
    if endpoint.secret == raw:
        return
    endpoint.secret = raw
    endpoint.save(update_fields=["secret"])
