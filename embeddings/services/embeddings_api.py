from google import genai
from openai import OpenAI


def get_openai_embeddings(texts, api_key, model):
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        input=texts,
        model=model,
    )
    return [value.embedding for value in response.data]


def get_gemini_embeddings(texts, api_key, model):
    gemini_client = genai.Client(api_key=api_key)
    result = gemini_client.models.embed_content(
        model=model,
        contents=texts,
    )
    return [embedding.values for embedding in result.embeddings]


EMBEDDING_MODELS = {
    "openai": {
        "method": get_openai_embeddings,
        "models": [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ],
    },
    "google": {"method": get_gemini_embeddings, "models": ["gemini-embedding-001"]},
}

def get_embeddings_from_model(texts, api_key, source, model):
    return EMBEDDING_MODELS[source]["method"](texts, api_key, model)


def get_models():
    return {key: value["models"] for key, value in EMBEDDING_MODELS.items()}
