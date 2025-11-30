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
    TextsSerializer,
)
from embeddings.service import get_embeddings_from_model, get_models
from ..models import EmbeddingLogs, TextEmbeddingPair


class GetEmbeddingsView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = EmbeddingLogs.objects.all()
    serializer_class = EmbeddingLogsSerializer

    def create_embedding_logs(self):
        embedding_logs_serializer = EmbeddingLogsSerializer(data=self.request.data)
        embedding_logs_serializer.is_valid(raise_exception=True)
        embedding_logs = embedding_logs_serializer.save()
        return embedding_logs

    def get_texts(self):
        texts_serializer = TextsSerializer(data=self.request.data)
        texts_serializer.is_valid(raise_exception=True)
        texts = texts_serializer.validated_data["texts"]
        return texts

    def post(self, request, *args, **kwargs):
        texts = self.get_texts()
        embedding_logs = self.create_embedding_logs()
        embeddings = get_embeddings_from_model(
            texts=texts,
            source=embedding_logs.source,
            model=embedding_logs.model,
            dimensions=embedding_logs.dimensions,
        )
        text_embedding_pairs = [
            TextEmbeddingPair(
                text=texts[i], embedding=embeddings[i], embedding_logs=embedding_logs
            )
            for i in range(len(texts))
        ]
        TextEmbeddingPair.objects.bulk_create(text_embedding_pairs)
        return Response(embeddings)

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
