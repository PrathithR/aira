"""
AIRA — Tool Registry

Central dictionary-based store for all registered tools.

Usage:
    registry = ToolRegistry()
    registry.register(EchoTool())

    tool = registry.get("echo")
    schemas = registry.get_tool_schemas()
"""

import logging
from typing import Iterator

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Dictionary-backed store for BaseTool instances.

    Keys are tool names (str). All lookups are O(1).
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Overwrites any existing tool with the same name.

        Args:
            tool: Any BaseTool subclass instance.
        """
        if tool.name in self._tools:
            logger.warning(
                "ToolRegistry: overwriting existing tool '%s'", tool.name
            )
        self._tools[tool.name] = tool
        logger.debug("ToolRegistry: registered tool '%s'", tool.name)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> BaseTool | None:
        """Return the tool registered under *name*, or None if not found.

        Args:
            name: Snake-case tool name matching the schema's function name.

        Returns:
            BaseTool instance or None.
        """
        return self._tools.get(name)

    # ------------------------------------------------------------------
    # Iteration / Schema Generation
    # ------------------------------------------------------------------

    def list_tools(self) -> list[str]:
        """Return the names of all registered tools in insertion order."""
        return list(self._tools.keys())

    def __iter__(self) -> Iterator[BaseTool]:
        """Iterate over registered tool instances."""
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)

    def get_tool_schemas(self) -> list[dict]:
        """Return OpenAI-style tool schemas for all registered tools.

        This is what gets passed as the ``tools`` argument to
        ``src.llm.complete()``.
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]
