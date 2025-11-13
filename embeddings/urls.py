from django.urls import path
from rest_framework.routers import DefaultRouter

from .api.views.embeddings_view import GetEmbeddingsView

router = DefaultRouter()

urlpatterns = router.urls
urlpatterns += [
    path("embeddings/", GetEmbeddingsView.as_view(), name="get_embeddings"),
]
