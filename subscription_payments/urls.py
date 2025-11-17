from .views import TestView
from django.urls import path

urlpatterns = [
    path("test/", TestView.as_view(), name="test"),
]
