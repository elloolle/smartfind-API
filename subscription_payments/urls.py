from subscription_payments.api.views import (
    SubscriptionView,
    TrialSubscriptionView,
    CustomerPortalView,
    PaymentMethodViewSet,
    PaymentViewSet,
    PaymentSession,
)
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("method", PaymentMethodViewSet, basename="payment-method")
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("subscription/", SubscriptionView.as_view(), name="subscription"),
    path("set_trial/", TrialSubscriptionView.as_view(), name="set_trial"),
    path("portal_link/", CustomerPortalView.as_view(), name="portal_link"),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path(
        "session/<str:payment_session_id>/",
        PaymentSession.as_view(),
        name="payment_session",
    ),
] + router.urls
