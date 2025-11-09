from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets
from ...services.EmbeddingsAPI import getEmbeddingsFromModel, getModels


class GetEmbeddingsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        embedding = getEmbeddingsFromModel(
            texts=request.data['texts'],
            APIKey=request.data['APIKey'],
            source=request.data['source'],
            model=request.data['model']
        )
        return Response(embedding)

    def get(self, request):
        print("dfsokijfjsik;kl")
        response = getModels()
        return Response(response)
