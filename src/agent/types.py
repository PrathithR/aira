from dataclasses import dataclass


@dataclass
class AgentResult:
    """Minimal result returned by Agent.run().

    Intentionally kept small for Phase 2.1.
    Future fields: tool_calls, usage, execution_metadata.
    """
    response: str
