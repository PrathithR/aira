from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """Metadata that describes a tool to the LLM.

    This is intentionally minimal for Phase 2.3.  Richer schemas
    (parameter definitions, required fields) will be added when
    concrete service tools are implemented.
    """
    name: str
    description: str
