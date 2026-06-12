from dataclasses import dataclass, field
from typing import Literal, Required, TypedDict

Role = Literal["system", "user", "assistant", "tool"]


class Message(TypedDict, total=False):
    role: Required[Role]
    content: str | None
    tool_calls: list[dict]    # present on assistant turns that call tools
    tool_call_id: str         # present on tool-result turns
    name: str


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict           # ALREADY json.loads'd — never a raw string


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = ""
    usage: Usage | None = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)
