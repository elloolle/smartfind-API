from django.conf import settings

from ..models import EmbeddingLogs, TextEmbeddingPair
from rest_framework import serializers
from pathlib import Path


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


class TextsSerializer(serializers.Serializer):
    texts = serializers.ListField(
        child=serializers.CharField(allow_blank=False), min_length=1
    )


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


class FileNameSerializer(serializers.Serializer):
    file_name = serializers.CharField()

    def validate_file_name(self, value):
        base_path = settings.STATIC_FILES_PATH.resolve()
        file_path = (base_path / Path(value)).resolve()
        if base_path not in file_path.parents and file_path != base_path:
            raise serializers.ValidationError(
                detail="file path is outside static files"
            )
        if not file_path.is_file():
            raise serializers.ValidationError(
                detail=f"{file_path} isn't a correct file name"
            )
        self.file_path = file_path
        return value
