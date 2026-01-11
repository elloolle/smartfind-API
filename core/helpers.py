from django.conf import settings
from loguru import logger
import django


def now():
    return django.utils.timezone.now()
