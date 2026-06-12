from unittest.mock import AsyncMock, MagicMock
import pytest
import litellm
from src.llm import (
    complete,
    LLMResponse,
    ToolCall,
    Usage,
    LLMError,
    LLMTimeoutError,
    LLMAuthError,
    LLMRateLimitError,
)
from src.settings import settings


# Helper mock structures
def make_mock_choice(content=None, tool_calls=None, finish_reason="stop"):
    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    return choice


def make_mock_raw_response(content=None, tool_calls=None, finish_reason="stop", usage=None):
    raw = MagicMock()
    raw.choices = [make_mock_choice(content, tool_calls, finish_reason)]
    if usage:
        raw.usage = MagicMock()
        raw.usage.prompt_tokens = usage.get("prompt_tokens", 0)
        raw.usage.completion_tokens = usage.get("completion_tokens", 0)
        raw.usage.total_tokens = usage.get("total_tokens", 0)
    else:
        raw.usage = None
    return raw


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear cached properties in settings if any."""
    # settings.active_api_key is a cached_property, so delete it from __dict__ if present
    # to avoid cache contamination between tests.
    if "active_api_key" in settings.__dict__:
        del settings.__dict__["active_api_key"]
    yield
    if "active_api_key" in settings.__dict__:
        del settings.__dict__["active_api_key"]


@pytest.mark.asyncio
async def test_text_response_normalization(monkeypatch):
    mock_response = make_mock_raw_response(content="hi", finish_reason="stop")
    mock_acompletion = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    # Mock settings fields so that active_api_key computes naturally
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    messages = [{"role": "user", "content": "hello"}]
    response = await complete(messages)

    assert isinstance(response, LLMResponse)
    assert response.text == "hi"
    assert response.tool_calls == []
    assert response.finish_reason == "stop"
    assert response.usage is None
    assert response.has_tool_calls is False


@pytest.mark.asyncio
async def test_tool_call_parsing(monkeypatch):
    # Mock tool call structure from LiteLLM
    mock_tc = MagicMock()
    mock_tc.id = "call_123"
    mock_tc.function = MagicMock()
    mock_tc.function.name = "get_weather"
    mock_tc.function.arguments = '{"location": "Seattle"}'

    mock_response = make_mock_raw_response(tool_calls=[mock_tc])
    mock_acompletion = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    messages = [{"role": "user", "content": "weather in seattle"}]
    response = await complete(messages)

    assert response.has_tool_calls is True
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].id == "call_123"
    assert response.tool_calls[0].name == "get_weather"
    assert response.tool_calls[0].arguments == {"location": "Seattle"}


@pytest.mark.asyncio
async def test_usage_mapping(monkeypatch):
    mock_response = make_mock_raw_response(
        content="ok",
        usage={"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
    )
    mock_acompletion = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    response = await complete([{"role": "user", "content": "hi"}])
    assert response.usage is not None
    assert response.usage.prompt_tokens == 12
    assert response.usage.completion_tokens == 8
    assert response.usage.total_tokens == 20


@pytest.mark.asyncio
async def test_model_switch_gemini(monkeypatch):
    mock_response = make_mock_raw_response(content="hi")
    mock_acompletion = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr(settings, "gemini_api_key", "gemini-test-key")

    await complete([{"role": "user", "content": "hi"}])

    mock_acompletion.assert_called_once()
    kwargs = mock_acompletion.call_args[1]
    assert kwargs["model"] == "gemini/gemini-2.0-flash"
    assert kwargs["api_key"] == "gemini-test-key"
    assert "api_base" not in kwargs


@pytest.mark.asyncio
async def test_model_switch_ollama(monkeypatch):
    mock_response = make_mock_raw_response(content="hi")
    mock_acompletion = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_model", "ollama/llama3")
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama:11434")

    await complete([{"role": "user", "content": "hi"}])

    mock_acompletion.assert_called_once()
    kwargs = mock_acompletion.call_args[1]
    assert kwargs["model"] == "ollama/llama3"
    assert kwargs["api_base"] == "http://ollama:11434"
    assert "api_key" not in kwargs


@pytest.mark.asyncio
async def test_error_mapping_timeout(monkeypatch):
    mock_acompletion = AsyncMock(
        side_effect=litellm.Timeout(
            message="timeout error",
            model="gemini/gemini-2.0-flash",
            llm_provider="gemini"
        )
    )
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    with pytest.raises(LLMTimeoutError):
        await complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_error_mapping_auth(monkeypatch):
    mock_acompletion = AsyncMock(
        side_effect=litellm.AuthenticationError(
            message="auth error",
            llm_provider="gemini",
            model="gemini/gemini-2.0-flash"
        )
    )
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    with pytest.raises(LLMAuthError):
        await complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_error_mapping_rate_limit(monkeypatch):
    mock_acompletion = AsyncMock(
        side_effect=litellm.RateLimitError(
            message="rate limit error",
            llm_provider="gemini",
            model="gemini/gemini-2.0-flash"
        )
    )
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    with pytest.raises(LLMRateLimitError):
        await complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_error_mapping_generic(monkeypatch):
    mock_acompletion = AsyncMock(side_effect=ValueError("some other error"))
    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    with pytest.raises(LLMError) as exc_info:
        await complete([{"role": "user", "content": "hi"}])
    assert not isinstance(exc_info.value, LLMTimeoutError)
    assert "LLM call failed" in str(exc_info.value)
