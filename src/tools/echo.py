"""
AIRA — Echo Tool

A zero-dependency tool that returns its input unchanged.

Purpose:
  - Validate the full LLM → Tool Call → Execution → Response pipeline
    without any external services or network calls.
  - Serve as the canonical example for how to implement a BaseTool.

Usage:
    registry = ToolRegistry()
    registry.register(EchoTool())
"""

from typing import Any

from src.tools.base import BaseTool


class EchoTool(BaseTool):
    """Reflects its *text* argument back to the caller unchanged."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return (
            "Echoes the provided text back exactly as given. "
            "Useful for testing the tool execution pipeline."
        )

    async def execute(self, text: str = "", **kwargs: Any) -> str:
        """Return *text* unchanged.

        Args:
            text: The string to echo.
            **kwargs: Ignored extra arguments (safe to pass through).

        Returns:
            Exactly *text*.
        """
        return text

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name":        self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type":        "string",
                            "description": "The text to echo back.",
                        },
                    },
                    "required": ["text"],
                },
            },
        }
