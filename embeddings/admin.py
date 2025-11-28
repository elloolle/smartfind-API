from django.contrib import admin

from embeddings.models import EmbeddingLogs, TextEmbeddingPair

admin.site.register(EmbeddingLogs)
admin.site.register(TextEmbeddingPair)
