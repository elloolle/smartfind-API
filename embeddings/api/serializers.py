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
        fields = ["source", "model", "dimensions"]

    def validate(self, attrs):
        source = attrs.get("source")
        model = attrs.get("model")
        if not settings.EMBEDDING_MODELS.get(source):
            raise serializers.ValidationError(detail="wrong source")
        if model not in settings.EMBEDDING_MODELS[source]["models"]:
            raise serializers.ValidationError(detail="wrong model")
        return attrs


class OnlyReadEmbeddingLogsSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmbeddingLogs
        fields = ["source", "model", "dimensions"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        text_embedding_pairs_serializer = TextEmbeddingPairSerializer(
            TextEmbeddingPair.objects.filter(embedding_logs=instance.id), many=True
        )
        data["text_embedding_pairs"] = text_embedding_pairs_serializer.data
        return data
