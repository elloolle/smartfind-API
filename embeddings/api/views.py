from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from embeddings.service import get_embeddings_from_model, get_models


class GetEmbeddingsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        embedding = get_embeddings_from_model(
            texts=request.data["texts"],
            source=request.data["source"],
            model=request.data["model"],
            dimensions=request.data.get("dimensions"),
        )
        return Response(embedding)

    def get(self, request):
        response = get_models()
        return Response(response)
