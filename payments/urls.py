from django.urls import path

from .views import *

urlpatterns = [
    path("webhook", StripeWebhook.as_view()),
    path("create-portal-session", CustomerPortal.as_view()),
    path("wait", WaitCheckoutComplete.as_view()),
    path("create-checkout-session", CreateCheckoutSession.as_view()),
    path("details", GetPaymentsDetails.as_view()),
    path("setup-auto-pay", SetupAutoPay.as_view()),
    path("promo-codes", PaymentsUtils.as_view({"post": "gen_promo_codes"})),
]
