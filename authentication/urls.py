from django.urls import path
from rest_framework.routers import DefaultRouter

from .api.views.AuthenticationView import UserView, AccessTokenView, LogoutView
router = DefaultRouter()
router.register("signup", UserView, basename="user")


urlpatterns = router.urls
urlpatterns += [
    path('login/', AccessTokenView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

]