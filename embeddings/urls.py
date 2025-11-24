from django.urls import path

from embeddings.api.views import GetEmbeddingsView

urlpatterns = [
    path("embeddings/", GetEmbeddingsView.as_view(), name="get_embeddings"),
]
