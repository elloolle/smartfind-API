from .base import *
import os
from dotenv import load_dotenv
from loguru import logger
from pathlib import Path

load_dotenv()

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",  # Specify the PostgreSQL backend
        "NAME": "smartfind_db",  # Name of your PostgreSQL database
        "USER": "admin",  # Username for connecting to the database
        "PASSWORD": "admin",  # Password for the database user
        "HOST": "localhost",  # Or the IP address/hostname of your PostgreSQL server
        "PORT": "5432",
    }
}

PRODUCTS = {
    "pro_month_subscription": {
        "plan": "pro",
        "month_price": 100,
        "delay": timedelta(days=30),
    },
    "default_subscription": {"plan": "free_plan", "month_price": 0, "delay": None},
}
TRIAL_PERIOD_DAYS = 14
DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION = 1
DEFAULT_TRIAL_PLAN = "pro"
SUCCESS_URL = "http://127.0.0.1:8000"

LOGS_PATH = Path.cwd() / "logs.txt"
logger.add(LOGS_PATH)

SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(days=1000)

IGNORE_CLONE_SUBSCRIPTIONS = True
IS_WEBHOOK_LOGGING_ON = True
WEBHOOKS_LOGS_PATH = (
    Path.cwd()
    / "subscription_payments"
    / "tests"
    / "webhook_test_events"
    / "first_sample.py"
)
WEBHOOKS_EVENT_NAME_TO_LOG = "customer.subscription.created"
