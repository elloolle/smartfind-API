from django.urls import path
from rest_framework.routers import DefaultRouter

from .api.views.authentication_view import AccessTokenView, LogoutView, UserSignUpView

router = DefaultRouter()

urlpatterns = router.urls
urlpatterns += [
    path("signup/", UserSignUpView.as_view(), name="signup"),
    path("login/", AccessTokenView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
