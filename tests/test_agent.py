"""
tests/test_agent.py

Unit tests for Agent core (Phase 2.1).

All tests are fully isolated:
  - complete() is mocked — no network calls.
  - No Gemini / OpenAI / Anthropic API usage.
  - No database access.

Test coverage:
  1. Basic conversation → AgentResult.response contains expected text.
  2. None response.text → AgentResult.response == "".
  3. Message construction → correct role/content structure sent to complete().
"""

from unittest.mock import AsyncMock, patch, call
import pytest

from src.agent import Agent, AgentResult
from src.agent.prompts import SYSTEM_PROMPT
from src.llm.types import LLMResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_llm_response(text: str | None = "Hello from LLM") -> LLMResponse:
    """Build a minimal LLMResponse with no tool calls."""
    return LLMResponse(
        text=text,
        tool_calls=[],
        finish_reason="stop",
        usage=None,
    )


# ---------------------------------------------------------------------------
# Test 1 — Basic conversation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_basic_conversation():
    """Agent.run() returns AgentResult whose .response matches the LLM text."""
    expected = "Hello from LLM"
    mock_response = make_llm_response(expected)

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = mock_response

        agent = Agent()
        result = await agent.run("Hello")

    assert isinstance(result, AgentResult)
    assert result.response == expected


# ---------------------------------------------------------------------------
# Test 2 — None response handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_none_response_becomes_empty_string():
    """When LLMResponse.text is None, AgentResult.response must be ''."""
    mock_response = make_llm_response(None)

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = mock_response

        agent = Agent()
        result = await agent.run("Say something")

    assert result.response == ""


# ---------------------------------------------------------------------------
# Test 3 — Message construction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_builds_correct_messages():
    """Agent sends [system, user] messages with correct roles and content."""
    user_input = "What time is it?"
    mock_response = make_llm_response("It is noon.")

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = mock_response

        agent = Agent()
        await agent.run(user_input)

    mock_complete.assert_called_once()
    positional_args, keyword_args = mock_complete.call_args

    # messages is the first positional argument
    messages = positional_args[0]

    assert len(messages) == 2

    system_msg = messages[0]
    assert system_msg["role"] == "system"
    assert system_msg["content"] == SYSTEM_PROMPT

    user_msg = messages[1]
    assert user_msg["role"] == "user"
    assert user_msg["content"] == user_input


# ---------------------------------------------------------------------------
# Test 4 — No tools → complete() called without tool schemas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_no_registry_passes_no_tools():
    """When no ToolRegistry is provided, tools= must be None in complete()."""
    mock_response = make_llm_response("ok")

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = mock_response

        agent = Agent()   # no registry
        await agent.run("hi")

    _, kwargs = mock_complete.call_args
    assert kwargs.get("tools") is None


# ---------------------------------------------------------------------------
# Test 5 — complete() is called exactly once per no-tool turn
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_single_llm_call_for_text_response():
    """Without tool calls, complete() is invoked exactly once."""
    mock_response = make_llm_response("just text")

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = mock_response

        agent = Agent()
        await agent.run("hello")

    assert mock_complete.call_count == 1
