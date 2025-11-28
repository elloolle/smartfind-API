from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.conf import settings


class EmbeddingLogs(models.Model):
    source = models.CharField(max_length=64)
    model = models.CharField(max_length=64)
    dimensions = models.IntegerField()


class TextEmbeddingPair(models.Model):
    text = models.TextField()
    embedding = ArrayField(models.FloatField())
    embedding_logs = models.ForeignKey(EmbeddingLogs, on_delete=models.CASCADE)
