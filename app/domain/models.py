from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str
    created_at: datetime = field(default_factory=utcnow)
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass(frozen=True)
class ModelReply:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: TokenUsage = TokenUsage()


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class AgentStep:
    iteration: int
    tool_name: str
    arguments: dict[str, Any]
    result_preview: str
    duration_ms: int


@dataclass(frozen=True)
class AgentResult:
    content: str
    usage: TokenUsage
    steps: tuple[AgentStep, ...]
    iterations: int


@dataclass(frozen=True)
class InteractionTrace:
    request_id: str
    client_id: str
    conversation_id: str
    model: str
    status: str
    user_message: str
    assistant_reply: str
    usage: TokenUsage
    iterations: int
    steps: tuple[AgentStep, ...]
    latency_ms: int
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
