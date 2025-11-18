import calendar
import contextlib
import copy
import datetime
import json
import os
import re
import hashlib

import django
import requests
from amplitude import BaseEvent
from django.conf import settings
from requests.adapters import HTTPAdapter
from rest_framework.response import Response

from config.configuration import amplitude_client, ENV_NAME, LOG_EVENTS, GA4_MEASUREMENT_ID, GA4_API_SECRET, \
    HTTP_RETRIES, IS_PROD
from django.db import connection, IntegrityError
from loguru import logger

from config.settings.base import SUBSCRIPTION_CHOICES_DICT


def success_response(data: dict | list | None = None, status_code=200):
    if data is None:
        data = {"status": "success"}
    return Response(data, status_code)


def ga4_send(client_id: str, event_name, params=None):
    # https://developers.google.com/analytics/devguides/collection/protocol/ga4?hl=ru
    # События появляются в Realtime overview, но сильно не сразу
    # Data Streams врут, что событий за последние 24 часа не было
    # TODO: make it async (any nonblocking option)
    params = params or {}

    payload = {
        'client_id': client_id,
        'events': {
            'name': event_name,
            'params': params
        }
    }
    url = f'https://www.google-analytics.com/mp/collect?measurement_id={GA4_MEASUREMENT_ID}&api_secret={GA4_API_SECRET}'
    response = requests.post(url, json=payload)
    if response.status_code // 100 != 2:
        logger.error("Google event sending error: {}", response.status_code)


def get_event_name(name):
    return ENV_NAME + "__" + name


def log_event(event_name, user_id=None, client_id=None, params=None, as_is=False, user=None):
    """
    user_id in amplitude is the username (only this have in landing and web)
    """
    if user:
        if not user_id:
            user_id = getattr(user, "username", None)
        if not client_id:
            client_id = getattr(user, "client_id", None)
    if not LOG_EVENTS:
        return
    if not as_is:
        event_name = get_event_name(event_name)
    logger.info("Logging event {} for user {} and client_id: {}", event_name, user_id, client_id)
    if not isinstance(user_id, str):
        logger.warning(f"User id {user_id} is not a string for event {event_name}")
    params = params or {}
    event = BaseEvent(event_type=event_name, user_id=user_id, event_properties=params)
    amplitude_client.track(event)
    ga4_send(client_id or user_id, event_name)
    from bitapi.analysis.models import UserEvent
    if user:
        UserEvent.objects.create(user=user, name=event_name, options=params)


def count_words(text):
    if not text:
        return 0
    return len(text.split())


def get_total_words(text, deep_scan=False, plagiarism_check=False):
    words = count_words(text)
    multiplier = 1
    if plagiarism_check:
        multiplier = 2
    return words * multiplier


def count_words_from_objects(items: list):
    """
    args:
    items: list[TextAnalysis]
    """
    result = 0
    for item in items:
        result += get_total_words(item.text, item.deep_scan, item.plagiarism_check)
    return result


def fetch_value(sql: str, *args):
    with connection.cursor() as cursor:
        cursor.execute(sql, args)
        response = cursor.fetchone()

    result = response[0] if response[0] is not None else None
    return result


def generate_text_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def is_valid_email(email):
    # Slightly Safer Version: r'^[a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if re.match(pattern, email):
        return True
    else:
        return False


def is_email(email: str | None) -> bool:
    if not isinstance(email, str):
        return False
    return is_valid_email(email)


main_session = requests.Session()
adapter = HTTPAdapter(max_retries=HTTP_RETRIES, pool_connections=10, pool_maxsize=100)
main_session.mount('http://', adapter)
main_session.mount('https://', adapter)


@contextlib.contextmanager
def requests_session():
    yield main_session


def get_subscription_options(subscription: str):
    return SUBSCRIPTION_CHOICES_DICT[subscription]


def get_limits(subscription: str, name: str) -> int | str | None:
    try:
        return SUBSCRIPTION_CHOICES_DICT[subscription][name]
    except KeyError:
        return None


def date_from_ts(ts):
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def now():
    return django.utils.timezone.now()


def get_next_month(dt: datetime.datetime) -> datetime.datetime:
    """
    Return a datetime shifted to the next month.

    - If the next month has the same day number, keep it.
    - If the next month has fewer days, use the maximum day of that month.
    - If dt is the last day of its month, always return the last day of the next month.
    - Year rolls over correctly when dt is in December.

    All other components (hour, minute, second, microsecond, tzinfo) are preserved.
    """
    # Determine current year, month, day
    year, month, day = dt.year, dt.month, dt.day

    # Find the last day of the current month
    last_day_current = calendar.monthrange(year, month)[1]

    # Compute next month and year
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # Find the last day of the next month
    last_day_next = calendar.monthrange(next_year, next_month)[1]

    # Determine the day for the result
    if day == last_day_current:
        # If dt is last day of current month, use last day of next month
        new_day = last_day_next
    else:
        # Otherwise, choose the same day or the max if not available
        new_day = min(day, last_day_next)

    # Preserve time components and tzinfo
    return datetime.datetime(
        year=next_year,
        month=next_month,
        day=new_day,
        hour=dt.hour,
        minute=dt.minute,
        second=dt.second,
        microsecond=dt.microsecond,
        tzinfo=dt.tzinfo
    )


def get_closest_reset_date(dt):
    """Ближайшая дата в прошлом, когда сбрасывались лимиты (должны были сбрасыаться)"""
    if dt is None:
        return now()
    while get_next_month(dt) <= now():
        dt = get_next_month(dt)
    return dt


def create_or_update(model, **kwargs):
    try:
        value = model.objects.get(pk=kwargs.get("id") or kwargs.get("pk"))
        for k, v in kwargs.items():
            setattr(value, k, v)
        value.save()
        return value
    except model.DoesNotExist:
        try:
            return model.objects.create(**kwargs)
        except IntegrityError:
            return create_or_update(model, **kwargs)


def add_values(dict1, dict2):
    dict1 = copy.deepcopy(dict1)
    for key, value in dict2.items():
        if isinstance(dict1.get(key), bool) or isinstance(value, bool):
            dict1[key] = value
            continue
        if isinstance(dict1.get(key), int) and isinstance(value, int):
            dict1[key] += value
        else:
            dict1[key] = value
    return dict1


def send_telegram_notification(message):
    """
    Send a notification to Telegram channel

    Args:
        message (str): Message text to send

    Returns:
        bool: True if message was sent successfully, False otherwise
    """

    if not IS_PROD:
        message = "[DEBUG]\n\n" + message

    url = f"https://api.telegram.org/bot{settings.TELEGRAM['bot_token']}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM["chat_id"],
        "text": message
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
        return True
    except Exception as e:
        logger.exception(f"Error sending Telegram notification: {str(e)}")
        return False

def to_snake_case(string: str) -> str:
    return string.replace(" ", "_").lower()

def save_tmp(filename, data):
    path = f"tmp/{filename}"
    os.makedirs("tmp", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)

def round_list(lst, digits=2):
    if not isinstance(lst, list):
        return lst
    return list(map(lambda x: round(x, digits), lst))

def get_first(item):
    if not item:
        return None
    if isinstance(item, list):
        return item[0]
    return item

def put_not_none(obj: dict, key: str, value):
    if value is None:
        return obj
    obj[key] = value
    return obj

def is_type_or_none(obj, type_):
    return obj is None or isinstance(obj, type_)
