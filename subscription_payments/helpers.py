from enum import Enum

import django
from django.conf import settings


def now():
    return django.utils.timezone.now()
