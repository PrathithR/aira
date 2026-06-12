import json
import logging
from typing import Any

import litellm

from src.settings import settings
from src.llm.types import LLMResponse, ToolCall, Usage, Message
from src.llm.errors import (
    LLMError,
    LLMTimeoutError,
    LLMAuthError,
    LLMRateLimitError,
)

logger = logging.getLogger(__name__)


async def complete(
    messages: list[Message],
    tools: list[dict] | None = None,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> LLMResponse:
    """Single model round-trip. build → call → normalize. Errors → LLMError."""
    request = _build_request(messages, tools, model, temperature, max_tokens)
    try:
        raw = await litellm.acompletion(**request)
    except litellm.Timeout as e:
        raise LLMTimeoutError(str(e)) from e
    except litellm.AuthenticationError as e:
        raise LLMAuthError(str(e)) from e
    except litellm.RateLimitError as e:
        raise LLMRateLimitError(str(e)) from e
    except Exception as e:
        logger.exception("LLM call failed")
        raise LLMError("LLM call failed") from e

    response = _to_response(raw)

    if settings.log_llm_responses:
        logger.debug("LLM response: %r", response)
    return response


def _build_request(
    messages: list[Message],
    tools: list[dict] | None,
    model: str | None,
    temperature: float | None,
    max_tokens: int | None,
) -> dict[str, Any]:
    """Resolve settings + overrides into litellm kwargs. Owns the Ollama branch."""
    request: dict[str, Any] = {
        "model":       model or settings.llm_model,
        "messages":    messages,
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens":  max_tokens or settings.llm_max_tokens,
        "num_retries": 2,        # let litellm own retry/backoff; don't reinvent
        "timeout":     60,
    }
    if tools:
        request["tools"] = tools

    if settings.llm_provider == "ollama":
        request["api_base"] = settings.ollama_base_url   # local; no key
    else:
        request["api_key"] = settings.active_api_key     # raises if missing

    return request


def _to_response(raw: Any) -> LLMResponse:
    """Normalize litellm's OpenAI-shaped response into our LLMResponse.
       This is the ONLY place that knows litellm's response shape."""
    choice = raw.choices[0]
    msg = choice.message

    tool_calls = [
        ToolCall(
            id=tc.id,
            name=tc.function.name,
            arguments=json.loads(tc.function.arguments or "{}"),  # str → dict
        )
        for tc in (getattr(msg, "tool_calls", None) or [])
    ]

    usage = None
    if getattr(raw, "usage", None):
        usage = Usage(
            prompt_tokens=raw.usage.prompt_tokens,
            completion_tokens=raw.usage.completion_tokens,
            total_tokens=raw.usage.total_tokens,
        )

    return LLMResponse(
        text=msg.content,
        tool_calls=tool_calls,
        finish_reason=choice.finish_reason,
        usage=usage,
    )
