from django.core.serializers import serialize
from django.http import FileResponse
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import generics, ReadOnlyModelViewSet

from .serializers import (
    EmbeddingLogsSerializer,
    TextEmbeddingPairSerializer,
    OnlyReadEmbeddingLogsSerializer,
    FileNameSerializer,
)
from embeddings.service import get_embeddings_from_model, get_models
from ..models import EmbeddingLogs


class GetEmbeddingsView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = EmbeddingLogs.objects.all()
    serializer_class = EmbeddingLogsSerializer

    def perform_create(self, serializer):
        embedding_logs = serializer.save()
        texts = self.request.data["texts"]
        embeddings = get_embeddings_from_model(
            texts=texts,
            source=embedding_logs.source,
            model=embedding_logs.model,
            dimensions=embedding_logs.dimensions,
        )
        text_embedding_pairs_data = [
            {
                "text": texts[i],
                "embedding": embeddings[i],
                "embedding_logs": embedding_logs.id,
            }
            for i in range(len(texts))
        ]
        text_embedding_pairs_serializer = TextEmbeddingPairSerializer(
            data=text_embedding_pairs_data, many=True
        )
        if not text_embedding_pairs_serializer.is_valid():
            logger.error(text_embedding_pairs_serializer.errors)
        else:
            text_embedding_pairs_serializer.save()
        self.embeddings = embeddings

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(self.embeddings)

    def get(self, request):
        response = get_models()
        return Response(response)


class EmbeddingLogsView(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = OnlyReadEmbeddingLogsSerializer
    queryset = EmbeddingLogs.objects.all()


class DownloadFileView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = FileNameSerializer

    def get(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        file_path = serializer.file_path
        return FileResponse(open(file_path, "rb"), as_attachment=True)
