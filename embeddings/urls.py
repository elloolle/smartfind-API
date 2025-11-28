from django.urls import path

from embeddings.api.views import GetEmbeddingsView, EmbeddingLogsView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("embeddings/logs", EmbeddingLogsView, basename="get-embedding-logs")
urlpatterns = [
    path("embeddings/", GetEmbeddingsView.as_view(), name="get_embeddings"),
] + router.urls
