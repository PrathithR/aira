import pytest
from src.llm import complete, LLMResponse
from src.settings import settings

# Apply integration marker to all tests in this module
pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_gemini_key():
    """Ensure a valid Gemini API key is configured dynamically before test execution."""
    key = settings.gemini_api_key
    if not key or key == "your_gemini_api_key_here" or "your_api_key" in key:
        pytest.skip("GEMINI_API_KEY is not configured or is a placeholder")


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch):
    """Ensure settings cache is cleared and provider is forced to gemini."""
    if "active_api_key" in settings.__dict__:
        del settings.__dict__["active_api_key"]
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini/gemini-2.5-flash")
    yield
    if "active_api_key" in settings.__dict__:
        del settings.__dict__["active_api_key"]


@pytest.mark.asyncio
async def test_integration_real_gemini_connectivity():
    """Verify end-to-end connectivity to the real Gemini API without raising exceptions."""
    messages = [
        {"role": "user", "content": "Ping"}
    ]
    try:
        response = await complete(messages)
    except Exception as e:
        pytest.fail(f"Connectivity check failed: {e}")

    assert response is not None
    assert response.text is not None
    assert len(response.text.strip()) > 0


@pytest.mark.asyncio
async def test_integration_basic_text_generation():
    """Verify that calling the real Gemini API returns the expected text response."""
    messages = [
        {"role": "user", "content": "Reply with exactly the word HELLO"}
    ]
    response = await complete(messages)

    assert response.text is not None
    assert "HELLO" in response.text.upper()


@pytest.mark.asyncio
async def test_integration_usage_extraction():
    """Verify that calling the real Gemini API extracts token usage data."""
    messages = [
        {"role": "user", "content": "Reply with exactly the word HELLO"}
    ]
    response = await complete(messages)

    assert response.usage is not None
    assert response.usage.prompt_tokens > 0
    assert response.usage.total_tokens > 0


@pytest.mark.asyncio
async def test_integration_response_normalization():
    """Verify that the response object is correctly normalized into our LLMResponse contract."""
    messages = [
        {"role": "user", "content": "Reply with exactly the word HELLO"}
    ]
    response = await complete(messages)

    assert isinstance(response, LLMResponse)
    assert response.finish_reason is not None
    assert response.finish_reason != ""
