from django.urls import path
from rest_framework.routers import SimpleRouter

from bitapi.users.views import UserActionsViewSet, GetMeView, UserRedirectView, UserUpdateView, UserDetailView, \
    SignUpLoginView, TestingUtil

router = SimpleRouter()

router.register("", UserActionsViewSet, basename='users')

app_name = "users"
urlpatterns = [
    *router.urls,
    path("me/", GetMeView.as_view()),
    path("util", TestingUtil.as_view()),
    path("signup/", SignUpLoginView.as_view()),
    path("~redirect/", view=UserRedirectView.as_view(), name="redirect"),
    path("~update/", view=UserUpdateView.as_view(), name="update"),
    path("<str:username>/", view=UserDetailView.as_view(), name="detail"),
]
