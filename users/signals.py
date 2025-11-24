from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from subscription_payments.models import Subscription


@receiver(post_save, sender=User)
def create_default_subscription(sender, instance, created, **kwargs):
    if created:
        Subscription.objects.create(user=instance)
