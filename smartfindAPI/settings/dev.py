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
DEFAULT_TRIAL_PLAN = "pro"
SUCCESS_URL = "http://127.0.0.1:8000"
LOGS_PATH = r"C:\Users\Leo\Desktop\Прога\SmartFind проект\smartfind-API\logs.txt"
