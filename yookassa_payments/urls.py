from django.conf import settings
from loguru import logger
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import WebHookView, SubscriptionView, TrialSubscriptionView

urlpatterns = [
    path("webhook/", WebHookView.as_view(), name="webhook"),
    path("subscription/", SubscriptionView.as_view(), name="subscription"),
    path("set_trial/", TrialSubscriptionView.as_view(), name="set_trial"),
]
