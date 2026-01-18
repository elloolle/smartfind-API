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
        "HOST": "postgres",  # Or the IP address/hostname of your PostgreSQL server
        "PORT": "5432",
    }
}

DEFAULT_PRODUCTS = [
    {
        "name": "pro_month_subscription",
        "plan": "pro",
        "month_price": 100,
        "delay": timedelta(days=30),
    },
    {
        "name": "default_subscription",
        "plan": "free_plan",
        "month_price": 0,
        "delay": None,
    },
]
DEFAULT_PRODUCT_NAME = "default_subscription"
TRIAL_PERIOD_DAYS = 14
DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION = 1
TRIAL_PRODUCT_NAME = "pro_month_subscription"
CHECKOUT_SUCCESS_URL = "http://127.0.0.1:8000"
CHECKOUT_CANCEL_URL = "http://127.0.0.1:8000"
PORTAL_SUCCESS_URL = "http://127.0.0.1:8000"
LOGS_PATH = Path.cwd() / "utils" / "logs.txt"
logger.add(LOGS_PATH)

SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(days=1000)

IGNORE_CLONE_SUBSCRIPTIONS = True

STRIPE_SECRET_KEY = os.environ["TEST_STRIPE_API_KEY"]
WEBHOOK_SECRET = os.environ["TEST_STRIPE_WEBHOOK_KEY"]

STATIC_FILES_PATH = BASE_DIR / Path("static/")
YOOKASSA_ACCOUNT_ID = os.environ.get("YOOKASSA_ACCOUNT_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")

CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
