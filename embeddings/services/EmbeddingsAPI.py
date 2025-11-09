from google import genai
from openai import OpenAI


def getOpenAIEmbeddings(texts, APIKey, model):
    client = OpenAI(api_key=APIKey)
    response = client.embeddings.create(
        input=texts,
        model=model
    )
    return [value.embedding for value in response.data]


def getGeminiEmbeddings(texts, APIKey, model):
    gemini_client = genai.Client(api_key=APIKey)
    result = gemini_client.models.embed_content(
        model=model,
        contents=texts,
    )
    return [embedding.values for embedding in result.embeddings]


getEmbeddingsModels = {
    "openai": {"method": getOpenAIEmbeddings,
               "models": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]},
    "google" : {"method": getGeminiEmbeddings, "models": ["gemini-embedding-001"]},
}


def getEmbeddingsFromModel(texts, APIKey, source, model):
    return getEmbeddingsModels[source]["method"](texts, APIKey, model)


def getModels():
    return {key : value["models"] for key, value in getEmbeddingsModels.items()}
