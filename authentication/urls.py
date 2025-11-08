from django.urls import path
from rest_framework.routers import DefaultRouter

from .api.views.AuthenticationView import CustomLoginView, LogoutView, UserView

router = DefaultRouter()
router.register("user", UserView, basename="user")


urlpatterns = router.urls + [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
