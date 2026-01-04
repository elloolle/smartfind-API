from django.conf import settings
from loguru import logger
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import WebHookView

urlpatterns = [
    path("webhook/", WebHookView.as_view(), name="webhook"),
]
