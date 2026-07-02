"""
AIRA — BaseTool abstract base class.

Every tool in the system must subclass BaseTool and implement ``execute()``.

Rules:
- Tools are stateless where possible.
- Tools raise plain Python exceptions on failure; the Agent catches them.
- Tools must NOT call complete() or any LLM API directly.
- Tools must NOT import from src.agent.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all AIRA tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique snake_case tool identifier (matches the function name in the schema)."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description used to generate the LLM tool schema."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given keyword arguments.

        Args:
            **kwargs: Arguments as parsed from the LLM tool-call response.

        Returns:
            A string result (or anything str()-able) that is passed back
            to the model as the tool result.

        Raises:
            Any exception — the Agent will catch it and report it to the
            model as a tool error.
        """
        raise NotImplementedError

    def to_openai_schema(self) -> dict:
        """Return the OpenAI function-calling tool schema for this tool.

        Subclasses that accept parameters MUST override this method
        and include a ``parameters`` key with a JSON-schema dict.

        Returns:
            A dict in the shape expected by LiteLLM / OpenAI tool calls.
        """
        return {
            "type": "function",
            "function": {
                "name":        self.name,
                "description": self.description,
                "parameters": {
                    "type":       "object",
                    "properties": {},
                    "required":   [],
                },
            },
        }
