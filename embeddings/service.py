from google import genai
from openai import OpenAI
from django.conf import settings
from google.genai import types
from functools import partial
from copy import deepcopy

def get_embeddings_with_OpenAI_lib(texts, model, dimensions, base_url, api_key):
    client = OpenAI(api_key=api_key, base_url=base_url)
    kwargs = {"input": texts, "model": model}
    if dimensions is not None:
        kwargs["dimensions"] = dimensions

    response = client.embeddings.create(**kwargs)
    return [value.embedding for value in response.data]

get_openai_embeddings = partial(
    get_embeddings_with_OpenAI_lib,
    base_url=None,
    api_key=settings.EMBEDDINGS_API_KEYS["openai"],
)

get_openrouter_embeddings = partial(
    get_embeddings_with_OpenAI_lib,
    base_url=settings.OPENROUTER_BASE_URL,
    api_key=settings.EMBEDDINGS_API_KEYS["openrouter"],
)

get_morphllm_embeddings = partial(
    get_embeddings_with_OpenAI_lib,
    base_url=settings.MORPHLM_BASE_URL,
    api_key=settings.EMBEDDINGS_API_KEYS["morphllm"],
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
settings.EMBEDDING_MODELS["morphllm"]["method"] = get_morphllm_embeddings


def get_embeddings_from_model(texts, source, model, dimensions=None):
    return settings.EMBEDDING_MODELS[source]["method"](texts, model, dimensions)


def get_models():
    models_info = deepcopy(settings.EMBEDDING_MODELS)
    for key in models_info.keys():
        del models_info[key]["method"]
    return models_info
