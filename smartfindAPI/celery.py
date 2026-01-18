from celery import Celery
import dotenv

dotenv.load_dotenv()


app = Celery("smartfindAPI")

app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()


@app.task
def add():
    n = 1
    for i in range(100):
        n *= i
    return n
