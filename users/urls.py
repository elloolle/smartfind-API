from django.urls import path
from rest_framework.routers import DefaultRouter

from users.api.views import (
    AccessTokenView,
    UserSignUpView,
    UserView,
)

urlpatterns = [
    path("signup/", UserSignUpView.as_view(), name="signup"),
    path("login/", AccessTokenView.as_view(), name="login"),
    path("", UserView.as_view(), name="user"),
]
