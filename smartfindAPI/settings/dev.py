from .base import *
import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = True

ALLOWED_HOSTS = ["*"]

PRODUCTS = {
    "pro_month_subscription": {
        "plan": "pro",
        "month_price": 100,
        "delay": timedelta(days=30),
    }
}
TRIAL_PERIOD_DAYS = 14
DAYS_BEFORE_SUBSCRIPTION_DEACTIVATION = 1
