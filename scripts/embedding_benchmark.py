import os
from typing import List, Optional
import logging
from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError, InternalServerError, AuthenticationError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Default timeout (seconds) for API calls
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))

# Read provider keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or None
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or None
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# Decide which provider to use.
# Accept an OpenRouter key supplied in either OPENROUTER_API_KEY OR mistakenly put into OPENAI_API_KEY (prefix sk-or-).
API_KEY: Optional[str] = None
BASE_URL: Optional[str] = None
KEY_SOURCE: Optional[str] = None

if OPENROUTER_API_KEY:
    API_KEY = OPENROUTER_API_KEY
    BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    KEY_SOURCE = "OPENROUTER"
elif OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-or-"):
    # Treat OpenAI env var containing an OpenRouter key as OpenRouter
    API_KEY = OPENAI_API_KEY
    BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    KEY_SOURCE = "OPENROUTER(via OPENAI_API_KEY)"
elif OPENAI_API_KEY:
    API_KEY = OPENAI_API_KEY
    BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    KEY_SOURCE = "OPENAI"

_client: Optional[OpenAI]
if API_KEY and BASE_URL:
    _client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    logger.debug("Embeddings client initialized (source=%s, base_url=%s)", KEY_SOURCE, BASE_URL)
else:
    _client = None
    logger.warning("No API key found. Set OPENAI_API_KEY or OPENROUTER_API_KEY in the environment.")

class EmbeddingError(Exception):
    pass


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """
    Compute embeddings for a list of texts and return list of vectors.
    - texts: list of str
    - model: optional override (defaults to EMBED_MODEL env var)
    """
    model = model or EMBED_MODEL

    if _client is None:
        raise EmbeddingError("No API key configured. Set OPENAI_API_KEY or OPENROUTER_API_KEY in your environment.")

    # remove empty list early
    if not texts:
        return []

    try:
        resp = _client.embeddings.create(model=model, input=texts, timeout=DEFAULT_TIMEOUT)
    except (APIError, AuthenticationError, RateLimitError, APITimeoutError, InternalServerError) as e:
        logger.exception("OpenAI embeddings API error: %s", e)
        raise EmbeddingError(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected embeddings error: %s", e)
        raise EmbeddingError(f"unexpected embedding error: {e}") from e

    raw = resp.to_dict() if hasattr(resp, "to_dict") else dict(resp)
    data = raw.get("data", []) if isinstance(raw, dict) else []
    vectors: List[List[float]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # safe extraction - providers vary on key name
        vec = item.get("embedding") or item.get("vector") or item.get("embedding_vector") or []
        if not vec and "values" in item:
            vec = item.get("values")
        vectors.append(vec)

    # sanity check: ensure returned vectors roughly match input count
    if len(vectors) != len(texts):
        logger.warning("Returned embeddings count (%d) != input count (%d)", len(vectors), len(texts))

    return vectors

def main():
    # simple test
    sample_texts = [
    "The quick brown fox jumps over the lazy dog.",
    "In a hole in the ground there lived a hobbit.",
    "To be, or not to be, that is the question.",
    "Artificial intelligence is transforming software development.",
    "Open-source models provide an affordable way to do embeddings."
]
    try:
        embeddings = embed_texts(sample_texts)
        for i, vec in enumerate(embeddings):
            print(f"Text: {sample_texts[i]}\nEmbedding (first 5 dims): {vec[:5]}\n")
    except EmbeddingError as e:
        print(f"Embedding error: {e}")
        
if __name__ == "__main__":
    main()