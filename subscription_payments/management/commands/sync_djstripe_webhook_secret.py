from django.conf import settings
from django.core.management.base import BaseCommand

from djstripe.models import WebhookEndpoint


class Command(BaseCommand):
    help = "Sync dj-stripe webhook secret from settings to the first endpoint."

    def handle(self, *args, **options):
        raw = getattr(settings, "WEBHOOK_SECRET", "")
        if not raw:
            self.stdout.write("WEBHOOK_SECRET is empty, nothing to do.")
            return

        endpoint = WebhookEndpoint.objects.first()
        if not endpoint:
            self.stdout.write("No WebhookEndpoint found.")
            return

        if endpoint.secret == raw:
            self.stdout.write("WebhookEndpoint secret is already up to date.")
            return

        endpoint.secret = raw
        endpoint.save(update_fields=["secret"])
        self.stdout.write("WebhookEndpoint secret updated.")
