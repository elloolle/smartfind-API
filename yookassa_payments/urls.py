from django.urls import path
from rest_framework.routers import DefaultRouter

from .api.views import (
    PaymentMethodViewSet,
    PaymentViewSet,
    SubscriptionView,
    TrialSubscriptionView,
    WebHookView,
)

router = DefaultRouter()
router.register("method", PaymentMethodViewSet, basename="payment-method")
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhook/", WebHookView.as_view(), name="webhook"),
    path("subscription/", SubscriptionView.as_view(), name="subscription"),
    path("set_trial/", TrialSubscriptionView.as_view(), name="set_trial"),
] + router.urls
