from django.conf import settings

from ..models import EmbeddingLogs, TextEmbeddingPair
from rest_framework import serializers


class TextEmbeddingPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextEmbeddingPair
        fields = ["text", "embedding", "embedding_logs"]


class EmbeddingLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmbeddingLogs
        fields = ["source", "model", "dimensions", "text_embedding_pairs"]

    def validate(self, attrs):
        source = attrs.get("source")
        model = attrs.get("model")
        if not settings.EMBEDDING_MODELS.get(source):
            raise serializers.ValidationError(detail="wrong source")
        if not settings.EMBEDDING_MODELS[source].get(model):
            raise serializers.ValidationError(detail="wrong model")
