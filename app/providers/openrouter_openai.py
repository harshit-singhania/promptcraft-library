# app/providers/openrouter_openai.py
import os
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError, InternalServerError, OpenAIError

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "openai/chatgpt-4o-latest")
DEFAULT_TIMEOUT = int(os.getenv("OPENROUTER_TIMEOUT", "60"))

# instantiate SDK client pointing to OpenRouter
_client = OpenAI(
    base_url=OPENROUTER_BASE,
    api_key=OPENROUTER_API_KEY or os.getenv("OPENAI_API_KEY"),
)


class ProviderError(Exception):
    pass


def _now_ms() -> int:
    return int(time.time() * 1000)


def call_chat_completions(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.0,
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synchronous call using OpenAI SDK routed to OpenRouter.

    Returns dict: {
      "text": <str>,
      "usage": <dict> (provider usage if present),
      "latency_ms": <int>,
      "raw": <provider json>
    }
    """
    model = model or DEFAULT_MODEL
    body = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
    }
    if max_tokens is not None:
        body["max_tokens"] = int(max_tokens)
    if extra_body:
        body.update(extra_body)

    headers = extra_headers or {}

    start = _now_ms()
    try:
        resp = _client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=body.get("max_tokens"),
            temperature=body.get("temperature"),
            extra_headers=headers,
            extra_body=extra_body or {},
            timeout=DEFAULT_TIMEOUT,
        )
    except (APIError, RateLimitError, APITimeoutError, InternalServerError) as e:
        raise ProviderError(str(e)) from e
    except Exception as e:
        raise ProviderError(f"unexpected provider error: {e}") from e

    latency_ms = _now_ms() - start

    # Extract text content defensively
    text = ""
    usage = {}
    raw = getattr(resp, "to_dict", lambda: resp)()
    try:
        # openai SDK returns an object with .choices
        # Safe extraction:
        if "choices" in raw and raw["choices"]:
            choice0 = raw["choices"][0]
            # Newer shape: choice0["message"]["content"]
            if "message" in choice0 and isinstance(choice0["message"], dict):
                # message.content might be string or a structured block
                msg_content = choice0["message"].get("content")
                if isinstance(msg_content, str):
                    text = msg_content
                else:
                    # if content is list/structured, join text parts
                    if isinstance(msg_content, list):
                        # some providers return structured pieces like {"type":"text","text":"..."}
                        parts = []
                        for chunk in msg_content:
                            if isinstance(chunk, dict) and "text" in chunk:
                                parts.append(chunk["text"])
                            elif isinstance(chunk, str):
                                parts.append(chunk)
                        text = "".join(parts)
                    else:
                        text = str(msg_content)
            else:
                # fallback: maybe choices[0].text
                text = choice0.get("text", "")
    except Exception:
        # be forgiving; store raw if extraction fails
        text = str(raw.get("choices", raw))

    # usage may be at top-level or nested; defensive extraction
    usage = raw.get("usage", {}) or raw.get("meta", {}).get("usage", {}) or {}

    return {"text": text, "usage": usage, "latency_ms": latency_ms, "raw": raw}