from subscription_payments.api.views import TestView, PaymentView
from django.urls import path
from rest_framework.routers import DefaultRouter

urlpatterns = [
    path("test/", TestView.as_view(), name="test"),
    path("", PaymentView.as_view(), name="payment"),
]
