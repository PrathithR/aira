"""
AIRA — Agent Core

The Agent is the central reasoning controller. It owns the message loop,
delegates LLM calls to src.llm, and dispatches tool calls to src.tools.

Phase 2 implementation covers:
  - Basic single-turn conversation (2.1)
  - Single-cycle tool execution (2.5)

NOT implemented yet:
  - Recursive ReAct loops
  - Memory / conversation history
  - Streaming
  - Database access
"""

import json
import logging
from typing import Sequence

from src.llm import complete
from src.llm.types import Message
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.types import AgentResult
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class Agent:
    """Stateless reasoning controller.

    Each call to ``run()`` is an independent request. The Agent has no
    memory between calls — conversation history must be passed in by
    the caller (future API layer).
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        """
        Args:
            registry: Optional ToolRegistry.  When provided, registered
                      tools are included in every LLM call and a single
                      tool-execution cycle is performed when the model
                      requests one.  When omitted the agent operates in
                      plain-text mode (Phase 2.1 behaviour).
        """
        self._registry = registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, user_input: str) -> AgentResult:
        """Execute a single agent turn.

        Flow (Phase 2.5):
            1. Build messages (system + user)
            2. Resolve tool definitions from registry (if any)
            3. Call complete()
            4. If the model requested a tool call → execute → second complete()
            5. Return AgentResult

        Args:
            user_input: The raw string from the user.

        Returns:
            AgentResult with the final text response.
        """
        messages: list[Message] = self._build_messages(user_input)
        tools = self._resolve_tool_schemas()

        logger.debug("Agent.run() starting | tools_available=%d", len(tools))

        # --- first LLM call -------------------------------------------
        response = await complete(messages, tools=tools or None)

        # --- single-cycle tool execution (Phase 2.5) ------------------
        if response.has_tool_calls and self._registry is not None:
            messages = await self._execute_tool_calls(messages, response.tool_calls)

            # second LLM call — model synthesises tool results
            response = await complete(messages)

        final_text = response.text or ""
        logger.debug("Agent.run() complete | response_length=%d", len(final_text))
        return AgentResult(response=final_text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_messages(self, user_input: str) -> list[Message]:
        """Construct the initial message list for an agent turn."""
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_input},
        ]

    def _resolve_tool_schemas(self) -> list[dict]:
        """Return the OpenAI-style tool-schema list for the active registry.

        Returns an empty list when no registry is configured, which causes
        ``complete()`` to be called without tool definitions (Phase 2.1).
        """
        if self._registry is None:
            return []
        return self._registry.get_tool_schemas()

    async def _execute_tool_calls(
        self,
        messages: list[Message],
        tool_calls: Sequence,
    ) -> list[Message]:
        """Execute every tool call requested by the model and append results.

        Appends:
          - The assistant turn (with tool_calls) to the message list.
          - One tool-result turn per tool call.

        Args:
            messages:   The message list *before* the assistant turn.
            tool_calls: ToolCall objects from LLMResponse.

        Returns:
            Extended message list ready for the follow-up LLM call.
        """
        # Reconstruct the assistant message that triggered tool calls.
        # LiteLLM / OpenAI protocol requires this turn to be present.
        assistant_tool_calls = [
            {
                "id":       tc.id,
                "type":     "function",
                "function": {
                    "name":      tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
            for tc in tool_calls
        ]
        messages = list(messages) + [
            {
                "role":       "assistant",
                "content":    None,
                "tool_calls": assistant_tool_calls,
            }
        ]

        # Execute each tool and append its result.
        for tc in tool_calls:
            logger.debug("Executing tool: %s | args=%r", tc.name, tc.arguments)
            tool = self._registry.get(tc.name)
            if tool is None:
                result = f"Error: tool '{tc.name}' is not registered."
                logger.warning("Unknown tool requested: %s", tc.name)
            else:
                try:
                    result = await tool.execute(**tc.arguments)
                    result = str(result)
                except Exception as exc:          # noqa: BLE001
                    result = f"Error executing tool '{tc.name}': {exc}"
                    logger.exception("Tool execution failed: %s", tc.name)

            messages.append(
                {
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "name":         tc.name,
                    "content":      result,
                }
            )

        return messages
