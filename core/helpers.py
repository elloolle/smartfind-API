import django
from datetime import datetime, timezone, UTC


def now():
    return django.utils.timezone.now()


def get_datetime_from_unix_timestamp(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp, tz=UTC)
