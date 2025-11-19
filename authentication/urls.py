from django.urls import path
from rest_framework.routers import DefaultRouter

from authentication.api.authentication_view import (
    AccessTokenView,
    LogoutView,
    UserSignUpView,
)

urlpatterns = [
    path("signup/", UserSignUpView.as_view(), name="signup"),
    path("login/", AccessTokenView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
