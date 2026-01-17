from celery import Celery
import dotenv
from datetime import timedelta
import json

dotenv.load_dotenv()


app = Celery("smartfindAPI")

app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()
# app.conf.beat_schedule = {
#     "test": {  # уникальное название задачи
#         "task": "yookassa_payments.tasks.withdraw_money_for_product",  # путь к задаче
#         "schedule": timedelta(seconds=10),
#         "kwargs": {
#             "payment_method_id": "30fdbb5b-000f-5000-b000-1de660e0e3a3",
#             "product_id": "pro_month_subscription",
#         },
#     }
# }
