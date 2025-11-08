from celery import Celery
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simple_django_project.settings")


app = Celery("main")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
