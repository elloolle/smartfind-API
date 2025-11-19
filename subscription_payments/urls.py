from subscription_payments.api.views import (
    SubscriptionView,
    WebhookView,
    TrialSubscriptionView,
    CustomerPortalView,
)
from django.urls import path
from rest_framework.routers import DefaultRouter

urlpatterns = [
    path("subscription/", SubscriptionView.as_view(), name="payment"),
    path("set_trial/", TrialSubscriptionView.as_view(), name="set_trial"),
    path("portal_link/", CustomerPortalView.as_view(), name="portal_link"),
    path("webhook/", WebhookView.as_view(), name="webhook"),
]
