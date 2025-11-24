from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ...services.embeddings_api import get_embeddings_from_model, get_models


class GetEmbeddingsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        embedding = get_embeddings_from_model(
            texts=request.data["texts"],
            api_key=request.data["APIKey"],
            source=request.data["source"],
            model=request.data["model"],
        )
        return Response(embedding)

    def get(self, request):
        response = get_models()
        return Response(response)
