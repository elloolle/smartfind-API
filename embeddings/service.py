from google import genai
from openai import OpenAI
from django.conf import settings
from google.genai import types

def get_embeddings_getter_with_OpenAI_lib(api_key, base_url=None):
    def embeddings_getter(texts, model, dimensions=None):
        client = OpenAI(api_key=api_key, base_url=base_url)
        kwargs = {"input": texts, "model": model}
        if dimensions is not None:
            kwargs["dimensions"] = dimensions

        response = client.embeddings.create(**kwargs)
        return [value.embedding for value in response.data]

    return embeddings_getter


get_openai_embeddings = get_embeddings_getter_with_OpenAI_lib(
    settings.EMBEDDINGS_API_KEYS["openai"]
)
get_openrouter_embeddings = get_embeddings_getter_with_OpenAI_lib(
    settings.EMBEDDINGS_API_KEYS["openrouter"], settings.OPENROUTER_BASE_URL
)


def get_gemini_embeddings(texts, model, dimensions=None):
    gemini_client = genai.Client(api_key=settings.EMBEDDINGS_API_KEYS["google"])
    result = gemini_client.models.embed_content(
        model=model,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=dimensions),
    )
    return [embedding.values for embedding in result.embeddings]


settings.EMBEDDING_MODELS["openai"]["method"] = get_openai_embeddings
settings.EMBEDDING_MODELS["google"]["method"] = get_gemini_embeddings
settings.EMBEDDING_MODELS["openrouter"]["method"] = get_openrouter_embeddings


def get_embeddings_from_model(texts, source, model, dimensions=None):
    return settings.EMBEDDING_MODELS[source]["method"](texts, model, dimensions)


def get_models():
    return {key: value["models"] for key, value in settings.EMBEDDING_MODELS.items()}
