from subscription_payments.api.views import (
    SubscriptionView,
    TrialSubscriptionView,
    CustomerPortalView,
    PaymentView,
)
from django.urls import path, include
from rest_framework.routers import DefaultRouter

urlpatterns = [
    path("subscription/", SubscriptionView.as_view(), name="payment"),
    path("set_trial/", TrialSubscriptionView.as_view(), name="set_trial"),
    path("portal_link/", CustomerPortalView.as_view(), name="portal_link"),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("", PaymentView.as_view(), name="payment"),
]
