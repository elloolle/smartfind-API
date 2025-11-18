from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, PositiveIntegerField, ForeignKey, Model, CASCADE, SET_NULL, BooleanField, \
    TextField, JSONField, IntegerField, DateTimeField, OneToOneField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from loguru import logger

from config.configuration import FUNC_LOGGER
from django.conf import settings
import pandas as pd
from django.utils import timezone
from datetime import timedelta
from bitapi.analysis.models import UserEvent
from bitapi.utils import is_email, get_limits, now, get_closest_reset_date
from bitapi.utils import send_telegram_notification
from bitapi.dynamic_config.models import ConfigModel


def find_user_utms(user):
    user_events = UserEvent.objects.filter(user=user, options__has_key='utm_source')
    return list(set([event.options['utm_source'] for event in user_events]))


class User(AbstractUser):
    SUBSCRIPTION_CHOICES = settings.SUBSCRIPTION_CHOICES
    REGISTRATION_TYPE_CHOICES = (("Email", "Email"), ("Google", "Google"), ("Github", "Github"), ("Crypto", "Crypto"))

    name = CharField(_("Name of User"), blank=True, max_length=255)
    address = CharField(max_length=40, blank=True, null=True)
    ip = CharField(max_length=40, blank=True, null=True)
    # TODO blank false
    privy_id = CharField(max_length=40, blank=True, null=True, unique=True)

    used_words_simple_scan = PositiveIntegerField(default=0)

    additional_limits = JSONField(default=dict)

    # ! Call with user.subscription_name() in code (Pay as you go added)
    # This field contain only Free, Premium or Enterprise, Educational
    subscription = CharField(choices=SUBSCRIPTION_CHOICES, default="Free")

    premium_or_custom_available_until = models.DateTimeField(null=True, blank=True)
    subscription_start_date = models.DateTimeField(null=True, blank=True)

    last_limits_updated = models.DateTimeField(null=True, blank=True, default=timezone.now)

    is_anon = BooleanField(default=False)
    # anon -> registered. registered -> last anon (login, signup)
    registered_user = ForeignKey('User', on_delete=SET_NULL, null=True, blank=True)
    enrolled = BooleanField(default=False)
    # TODO: Move to UserOptions
    onboarding_completed = BooleanField(default=False)
    role = CharField(max_length=200, null=True, blank=True)
    client_id = CharField(null=True)
    registration_type = CharField(max_length=20, blank=True, null=True)

    customer_id = CharField(max_length=200, null=True, blank=True)
    unsubscribed_emails = BooleanField(default=False)
    grant_credits_cents = IntegerField(default=0, null=False)
    popup = CharField(max_length=32, null=True, blank=True)

    def subscription_name(self):
        subscription = self.subscription
        if subscription != "Free":
            return subscription
        if not self.additional_limits:
            return subscription
        if not any(self.additional_limits.values()):
            return subscription
        return "Pay as you go"

    def is_free(self):
        return self.subscription_name() == "Free"

    def get_limit(self, name: str):
        additional = self.additional_limits or {}
        if name in additional:
            return additional[name]
        return get_limits(self.subscription_name(), name)

    def get_remaining_limit(self, name: str):
        self.update_usage()
        additional = self.additional_limits or {}
        subscription_limit = get_limits(self.subscription, f"granted_{name}")
        return subscription_limit - getattr(self, f"used_{name}") + additional.get(f"granted_{name}", 0)

    def get_subscription(self):
        from bitapi.payments.views import get_user_sub_db
        return get_user_sub_db(self)

    def reset_usage(self):
        logger.info("Reset usage")
        additional_limits = dict(self.additional_limits or {})
        limits = [
            "words_simple_scan",
            "british_words"
        ]
        for limit in limits:
            if f"granted_{limit}" not in additional_limits:
                continue
            used = getattr(self, f"used_{limit}", 0)
            # used more than granted in subscription
            additional_limits[f"granted_{limit}"] -= max(0, used - get_limits(self.subscription, f"granted_{limit}"))
            setattr(self, f"used_{limit}", 0)
        self.save(update_fields=["used_words_simple_scan", "additional_limits"])

    def cancel_subscription(self):
        self.subscription = "Free"
        self.premium_or_custom_available_until = None
        self.last_limits_updated = now()
        self.save(update_fields=["subscription", "premium_or_custom_available_until", "last_limits_updated"])
        self.reset_usage()

    def update_usage(self):
        # One extra day for subscription charge attempts,
        # ensures that the subscription will be not cancelled, if card still valid
        if self.premium_or_custom_available_until and self.premium_or_custom_available_until + timedelta(
            days=1) < now():
            logger.info("User {} subscription expired", self.id)
            self.cancel_subscription()
            return

        reset_date = get_closest_reset_date(self.last_limits_updated)
        if reset_date != self.last_limits_updated:
            # Нужно было сбросить, делаем это сейчас (в промежутке не было запросов, так что все окей)
            logger.info("Will update usage: {}", reset_date)
            self.last_limits_updated = reset_date
            self.save(update_fields=["last_limits_updated"])
            self.reset_usage()

    first_name = None  # type: ignore
    last_name = None  # type: ignore

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    @classmethod
    def map_registration_type(cls):
        df = pd.read_csv('./user_data.csv')
        for user in cls.objects.all():
            if user.username in df['email'].values:
                user.registration_type = 'Google'
            elif user.username.startswith('0x'):
                user.registration_type = 'Crypto'
            elif is_email(user.username):
                user.registration_type = 'Email'
            else:
                user.registration_type = 'Github'
            user.save(update_fields=['registration_type'])


class UserOptions(Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='options',
    )
    policy_accepted = BooleanField(default=False)
    policy_version = CharField(max_length=50, null=True, blank=True)
    policy_timestamp = DateTimeField(null=True, blank=True)
    policy_ip = CharField(max_length=40, null=True, blank=True)
    feedback = JSONField(null=True, blank=True)
    overrides = JSONField(null=False, default=dict, blank=True)


class SubscribeRequest(Model):
    user = ForeignKey(User, on_delete=CASCADE)
    is_free = BooleanField(default=False)
    role_name = CharField(max_length=500, null=True, blank=True)

    date_created = DateTimeField(auto_now_add=True)
    date_updated = DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


class Questionnaire(Model):
    work_place = CharField(max_length=500, blank=True, null=True)
    company_name = CharField(max_length=500, blank=True, null=True)
    job_title = CharField(max_length=500, blank=True, null=True)
    job_position = CharField(max_length=500, blank=True, null=True)
    ai_detector_purpose = TextField(blank=True)
    current_solution = TextField(blank=True)
    discovery_source = CharField(max_length=500, blank=True)
    other_tools = TextField(blank=True)
    important_features = TextField(blank=True)

    user = ForeignKey(User, on_delete=CASCADE)

    def __str__(self):
        return f"Questionnaire for {self.user.username}"


class SocialMediaSubscribeRequest(Model):
    SOURCE_CHOICES = (
        ("twitter", "Twitter"),
        ("linkedin", "LinkedIn"),
        ("facebook", "Facebook"),
    )

    source = CharField(max_length=20, choices=SOURCE_CHOICES)
    link_url = CharField(max_length=500)
    user = ForeignKey(User, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = BooleanField(default=False)

    def __str__(self):
        return f"Social Media Subscribe Request by {self.user.username} on {self.source}"

    def send_telegram_notification(self):
        from bitapi.utils import send_telegram_notification

        message = (
            f"New Social Media Subscribe Request:\n"
            f"Name: {self.user.name}\n"
            f"Id: {self.user.id}\n"
            f"Source: {self.source}\n"
            f"Link: {self.link_url}\n"
            f"Email: {self.user.username}"
        )

        send_telegram_notification(message)


@receiver(post_save, sender=SocialMediaSubscribeRequest)
@FUNC_LOGGER
def handle_social_media_approval(sender, instance, created, **kwargs):
    """
    Signal handler to ensure premium subscription is granted when a social media request is approved.
    This provides an additional safety mechanism beyond the save method.
    """
    if not created and instance.approved:
        user = instance.user
        if user.subscription != 'Premium' or user.premium_or_custom_available_until is None or user.premium_or_custom_available_until < now():
            user.subscription = 'Premium'
            send_telegram_notification(
                f"Social Media Subscribe Approved - Premium granted:\n"
                f"Name: {user.name}\n"
                f"Id: {user.id}\n"
            )
            user.premium_or_custom_available_until = now() + timedelta(days=30)
            user.save(update_fields=['subscription', 'premium_or_custom_available_until'])
