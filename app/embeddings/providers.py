# app/embeddings/provider.py

import os
from typing import List
import logging
from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError, InternalServerError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") 
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# Decide base URL and key
if OPENROUTER_API_KEY:
    BASE_URL = "https://openrouter.ai/api/v1"
    API_KEY = OPENROUTER_API_KEY

_client = OpenAI(
    base_url=BASE_URL or "https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

class EmbeddingError(Exception):
    pass


def embed_texts(texts: List[str], model: str | None = None) -> List[List[float]]:
    """
    Compute embeddings for a list of texts and return list of vectors.
    - texts: list of str
    - model: optional override (defaults to EMBED_MODEL env var)
    """
    model = model or EMBED_MODEL
    if not OPENROUTER_API_KEY:
        raise EmbeddingError("OPENROUTER_API_KEY not set in env")

    # remove empty strings early
    if not texts:
        return []

    try:
        # new OpenAI SDK: client.embeddings.create(model=..., input=[...])
        resp = _client.embeddings.create(model=model, input=texts, timeout=DEFAULT_TIMEOUT)
    except (APIError, RateLimitError, APITimeoutError, InternalServerError) as e:
        logger.exception("OpenAI embeddings API error: %s", e)
        raise EmbeddingError(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected embeddings error: %s", e)
        raise EmbeddingError(f"unexpected embedding error: {e}") from e

    raw = resp.to_dict() if hasattr(resp, "to_dict") else dict(resp)
    data = raw.get("data", [])
    vectors: List[List[float]] = []
    for item in data:
        # safe extraction - providers vary on key name
        vec = item.get("embedding") or item.get("vector") or item.get("embedding_vector") or []
        if not vec and "values" in item:
            vec = item.get("values")
        vectors.append(vec)

    # sanity check: ensure returned vectors match input count
    if len(vectors) != len(texts):
        logger.warning("Returned embeddings count (%d) != input count (%d)", len(vectors), len(texts))

    return vectors