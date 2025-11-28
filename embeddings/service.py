from functools import partial

from google import genai
from openai import OpenAI
from django.conf import settings
from google.genai import types
from typing import Callable


def get_embeddings_with_OpenAI_lib(
    texts: list[str],
    model: str,
    dimensions: int | None,
    base_url: str | None,
    api_key: str,
) -> list[list[float]]:
    client = OpenAI(api_key=api_key, base_url=base_url)
    if dimensions is None:
        response = client.embeddings.create(input=texts, model=model)
    else:
        response = client.embeddings.create(
            input=texts, model=model, dimensions=dimensions
        )
    return [value.embedding for value in response.data]


get_openai_embeddings: Callable[[list[str], str, int | None], list[list[float]]] = (
    partial(
        get_embeddings_with_OpenAI_lib,
        base_url=None,
        api_key=settings.EMBEDDINGS_API_KEYS["openai"],
    )
)
GetEmbeddingsFromModelType = Callable[[list[str], str, int | None], list[list[float]]]

get_openrouter_embeddings: GetEmbeddingsFromModelType = partial(
    get_embeddings_with_OpenAI_lib,
    base_url=settings.OPENROUTER_BASE_URL,
    api_key=settings.EMBEDDINGS_API_KEYS["openrouter"],
)

get_morphllm_embeddings: GetEmbeddingsFromModelType = partial(
    get_embeddings_with_OpenAI_lib,
    base_url=settings.MORPHLM_BASE_URL,
    api_key=settings.EMBEDDINGS_API_KEYS["morphllm"],
)


def get_gemini_embeddings(
    texts: list[str], model: str, dimensions: int | None = None
) -> list[list[float]]:
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
settings.EMBEDDING_MODELS["morphllm"]["method"] = get_morphllm_embeddings


def get_embeddings_from_model(
    texts: list[str], source: str, model: str, dimensions: str | None = None
):
    return settings.EMBEDDING_MODELS[source]["method"](texts, model, dimensions)


def get_models() -> dict[str, object]:
    models_info = settings.EMBEDDING_MODELS.copy()
    for key in models_info.keys():
        del models_info[key]["method"]
    return models_info
