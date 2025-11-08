from django.urls import path
from rest_framework.routers import DefaultRouter

from .api.views.AuthenticationView import CustomLoginView, LogoutView, UserView
from .api.views.ModeratorView import TextModeratorView, ImageModeratorView, VideoModeratorView

router = DefaultRouter()
router.register("text", TextModeratorView, basename="moderate/text")
router.register("image", ImageModeratorView, basename="moderate/image")
router.register("video", VideoModeratorView, basename="moderate/video")
router.register("user", UserView, basename="user")

urlpatterns = router.urls + [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
