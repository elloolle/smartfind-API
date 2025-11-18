from subscription_payments.api.views import TestView, PaymentView, WebhookView
from django.urls import path
from rest_framework.routers import DefaultRouter

urlpatterns = [
    path("test/", TestView.as_view(), name="test"),
    path("", PaymentView.as_view(), name="payment"),
    path("webhook/", WebhookView.as_view(), name="webhook"),
]
