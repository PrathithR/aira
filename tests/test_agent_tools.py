"""
tests/test_agent_tools.py

Unit tests for Agent tool execution (Phase 2.5 / 2.6).

All tests are fully isolated:
  - complete() is mocked — no network calls.
  - Tools are mocked or use the real EchoTool (no external deps).
  - No Gemini / OpenAI / Anthropic API usage.
  - No database access.

Test coverage:
  1. Tool call detected in LLM response.
  2. Correct tool selected from registry.
  3. Tool executed with parsed arguments.
  4. Tool result appended to messages.
  5. Final answer returned from second complete() call.
  6. Unknown tool → error string, not exception.
  7. Tool execution failure → error string, not exception.
  8. No tool calls → single complete() call (regression guard).
  9. Registry with EchoTool → schemas passed to complete().
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

from src.agent import Agent, AgentResult
from src.llm.types import LLMResponse, ToolCall
from src.tools import EchoTool, ToolRegistry


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

def make_tool_call(name: str, arguments: dict, call_id: str = "call_001") -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments)


def make_llm_response(
    text: str | None = None,
    tool_calls: list[ToolCall] | None = None,
    finish_reason: str = "stop",
) -> LLMResponse:
    return LLMResponse(
        text=text,
        tool_calls=tool_calls or [],
        finish_reason=finish_reason,
        usage=None,
    )


def make_registry_with_echo() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTool())
    return registry


# ---------------------------------------------------------------------------
# Test 1 — Tool call detected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_call_detected():
    """When LLMResponse.has_tool_calls is True, Agent enters the tool loop."""
    tc = make_tool_call("echo", {"text": "hello"})
    first_response  = make_llm_response(tool_calls=[tc])
    second_response = make_llm_response(text="Done")

    registry = make_registry_with_echo()

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [first_response, second_response]

        agent  = Agent(registry=registry)
        result = await agent.run("echo hello")

    # complete() must be called twice: once to get tool call, once for final answer
    assert mock_complete.call_count == 2
    assert result.response == "Done"


# ---------------------------------------------------------------------------
# Test 2 — Correct tool selected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_correct_tool_selected_from_registry():
    """Agent selects the tool matching the LLM-requested name."""
    tc = make_tool_call("echo", {"text": "ping"})
    first_response  = make_llm_response(tool_calls=[tc])
    second_response = make_llm_response(text="pong")

    # Use a spy tool to confirm it was called
    spy_tool = MagicMock()
    spy_tool.name = "echo"
    spy_tool.description = "echo tool"
    spy_tool.execute = AsyncMock(return_value="ping")
    spy_tool.to_openai_schema = EchoTool().to_openai_schema

    registry = ToolRegistry()
    registry.register(spy_tool)

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [first_response, second_response]
        agent = Agent(registry=registry)
        await agent.run("test")

    spy_tool.execute.assert_called_once_with(text="ping")


# ---------------------------------------------------------------------------
# Test 3 — Tool executed with parsed arguments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_executed_with_correct_arguments():
    """Arguments from the LLM tool call are unpacked as kwargs to execute()."""
    tc = make_tool_call("echo", {"text": "Hello, World!"})
    first_response  = make_llm_response(tool_calls=[tc])
    second_response = make_llm_response(text="Got it")

    registry = make_registry_with_echo()

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [first_response, second_response]
        agent = Agent(registry=registry)
        await agent.run("test")

    # Inspect the messages sent to the second complete() call
    second_call_messages = mock_complete.call_args_list[1][0][0]
    tool_result_msg = next(
        m for m in second_call_messages if m.get("role") == "tool"
    )
    # EchoTool returns the text unchanged
    assert tool_result_msg["content"] == "Hello, World!"
    assert tool_result_msg["name"] == "echo"


# ---------------------------------------------------------------------------
# Test 4 — Tool result appended to messages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_result_appended_to_messages():
    """After execution the message list contains the tool-result turn."""
    tc = make_tool_call("echo", {"text": "check"}, call_id="call_abc")
    first_response  = make_llm_response(tool_calls=[tc])
    second_response = make_llm_response(text="acknowledged")

    registry = make_registry_with_echo()

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [first_response, second_response]
        agent = Agent(registry=registry)
        await agent.run("check")

    second_call_messages = mock_complete.call_args_list[1][0][0]

    # Should have: system, user, assistant (tool_calls), tool result
    roles = [m["role"] for m in second_call_messages]
    assert "tool" in roles

    tool_msg = next(m for m in second_call_messages if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "call_abc"
    assert tool_msg["content"] == "check"


# ---------------------------------------------------------------------------
# Test 5 — Final answer returned from second complete()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_final_answer_comes_from_second_complete():
    """AgentResult.response equals the text from the second LLM call."""
    tc = make_tool_call("echo", {"text": "x"})
    first_response  = make_llm_response(tool_calls=[tc])
    second_response = make_llm_response(text="The final answer is 42.")

    registry = make_registry_with_echo()

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [first_response, second_response]
        agent = Agent(registry=registry)
        result = await agent.run("give me the answer")

    assert result.response == "The final answer is 42."


# ---------------------------------------------------------------------------
# Test 6 — Unknown tool → error string, not exception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_tool_returns_error_string():
    """When the LLM requests an unregistered tool, Agent returns an error
    string to the model rather than raising."""
    tc = make_tool_call("nonexistent_tool", {"x": 1})
    first_response  = make_llm_response(tool_calls=[tc])
    second_response = make_llm_response(text="I see the error.")

    # empty registry — no tools registered
    registry = ToolRegistry()

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [first_response, second_response]
        agent = Agent(registry=registry)
        result = await agent.run("call something")

    # Should not raise — should still call complete() a second time
    assert mock_complete.call_count == 2
    second_call_messages = mock_complete.call_args_list[1][0][0]
    tool_msg = next(m for m in second_call_messages if m["role"] == "tool")
    assert "not registered" in tool_msg["content"]


# ---------------------------------------------------------------------------
# Test 7 — Tool execution failure → error string, not exception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_execution_failure_becomes_error_string():
    """If a tool's execute() raises, the Agent catches it and passes
    a descriptive error string back to the model."""
    tc = make_tool_call("broken_tool", {"arg": "val"})
    first_response  = make_llm_response(tool_calls=[tc])
    second_response = make_llm_response(text="Handled.")

    broken_tool = MagicMock()
    broken_tool.name = "broken_tool"
    broken_tool.description = "always fails"
    broken_tool.execute = AsyncMock(side_effect=RuntimeError("boom"))
    broken_tool.to_openai_schema = lambda: {
        "type": "function",
        "function": {"name": "broken_tool", "description": "always fails",
                     "parameters": {"type": "object", "properties": {}, "required": []}},
    }

    registry = ToolRegistry()
    registry.register(broken_tool)

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [first_response, second_response]
        agent = Agent(registry=registry)
        result = await agent.run("break it")

    # Should not raise
    assert mock_complete.call_count == 2
    second_call_messages = mock_complete.call_args_list[1][0][0]
    tool_msg = next(m for m in second_call_messages if m["role"] == "tool")
    assert "Error executing tool" in tool_msg["content"]


# ---------------------------------------------------------------------------
# Test 8 — No tool calls → single complete() (regression guard)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_tool_calls_single_complete_call():
    """If the LLM responds with text only, complete() is called exactly once,
    even when a registry is configured."""
    text_only = make_llm_response(text="Plain text response.")
    registry  = make_registry_with_echo()

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = text_only
        agent = Agent(registry=registry)
        result = await agent.run("hello")

    assert mock_complete.call_count == 1
    assert result.response == "Plain text response."


# ---------------------------------------------------------------------------
# Test 9 — Registry tool schemas passed to complete()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registry_schemas_passed_to_complete():
    """When a registry is configured, its tool schemas are included
    in the first complete() call."""
    text_only = make_llm_response(text="ok")
    registry  = make_registry_with_echo()

    with patch("src.agent.agent.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = text_only
        agent = Agent(registry=registry)
        await agent.run("list tools")

    _, first_kwargs = mock_complete.call_args_list[0]
    passed_tools = first_kwargs.get("tools")
    assert passed_tools is not None
    assert len(passed_tools) == 1
    assert passed_tools[0]["function"]["name"] == "echo"
