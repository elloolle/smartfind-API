from copy import deepcopy
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from embeddings.models import EmbeddingLogs, TextEmbeddingPair


class GetEmbeddingsViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("get_embeddings")
        self.base_payload = {
            "source": "openai",
            "model": "text-embedding-3-small",
            "dimensions": 1536,
            "texts": ["alpha", "beta"],
        }
        self.mock_embeddings = [
            [0.01, 0.02],
            [0.03, 0.04],
        ]

    def _build_payload(self, **overrides):
        payload = deepcopy(self.base_payload)
        payload.update(overrides)
        return payload

    def _post(self, **overrides):
        payload = self._build_payload(**overrides)
        response = self.client.post(self.url, data=payload, format="json")
        return response, payload

    @patch("embeddings.api.views.get_embeddings_from_model")
    def test_returns_embeddings_when_payload_is_valid(self, mock_get_embeddings):
        mock_get_embeddings.return_value = self.mock_embeddings

        response, payload = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.mock_embeddings)
        mock_get_embeddings.assert_called_once_with(
            texts=payload["texts"],
            source=payload["source"],
            model=payload["model"],
            dimensions=payload["dimensions"],
        )
        self.assertEqual(EmbeddingLogs.objects.count(), 1)
        self.assertEqual(
            TextEmbeddingPair.objects.count(),
            len(payload["texts"]),
        )
        first_pair = TextEmbeddingPair.objects.order_by("id").first()
        self.assertIsNotNone(first_pair)
        self.assertEqual(first_pair.text, payload["texts"][0])
        self.assertEqual(first_pair.embedding, self.mock_embeddings[0])

    @patch("embeddings.api.views.get_embeddings_from_model")
    def test_creates_pairs_for_multiple_texts(self, mock_get_embeddings):
        texts = ["sample"] * 5
        embeddings = [[float(i), float(i + 1)] for i in range(len(texts))]
        mock_get_embeddings.return_value = embeddings

        response, payload = self._post(texts=texts)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, embeddings)
        self.assertEqual(TextEmbeddingPair.objects.count(), len(texts))
        stored_texts = list(
            TextEmbeddingPair.objects.order_by("id").values_list("text", flat=True)
        )
        self.assertEqual(stored_texts, payload["texts"])

    @patch("embeddings.api.views.get_embeddings_from_model")
    def test_returns_400_when_source_is_invalid(self, mock_get_embeddings):
        response, _ = self._post(source="invalid-source")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"non_field_errors": ["wrong source"]})
        mock_get_embeddings.assert_not_called()
        self.assertEqual(EmbeddingLogs.objects.count(), 0)

    @patch("embeddings.api.views.get_embeddings_from_model")
    def test_returns_400_when_model_is_not_allowed(self, mock_get_embeddings):
        response, _ = self._post(model="not-supported")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"non_field_errors": ["wrong model"]})
        mock_get_embeddings.assert_not_called()
        self.assertEqual(EmbeddingLogs.objects.count(), 0)

    @patch("embeddings.api.views.get_embeddings_from_model")
    def test_return_400_when_text_is_empty(self, mock_get_embeddings):
        response, _ = self._post(texts=[])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_get_embeddings.assert_not_called()
        self.assertEqual(EmbeddingLogs.objects.count(), 0)

    @patch("embeddings.api.views.get_embeddings_from_model")
    def test_return_400_when_text_is_not_list(self, mock_get_embeddings):
        response, _ = self._post(texts="abcd")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_get_embeddings.assert_not_called()
        self.assertEqual(EmbeddingLogs.objects.count(), 0)
