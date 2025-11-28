from django.urls import path

from embeddings.api.views import GetEmbeddingsView, EmbeddingLogsView, DownloadFileView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("logs/", EmbeddingLogsView, basename="get-embedding-logs")
urlpatterns = [
    path("", GetEmbeddingsView.as_view(), name="get_embeddings"),
    path("download-local/", DownloadFileView.as_view(), name="download_file"),
] + router.urls
