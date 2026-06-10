from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from app.domain.models import (
    InteractionTrace,
    Message,
    ModelReply,
    RateLimitDecision,
    ToolSpec,
)


class ChatModelPort(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    async def generate(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
        allow_tool_use: bool = True,
    ) -> ModelReply: ...


class ConversationRepository(ABC):
    @abstractmethod
    async def get(self, conversation_id: str) -> list[Message] | None: ...

    @abstractmethod
    async def append(self, conversation_id: str, messages: Sequence[Message]) -> None: ...


class MarketDataPort(ABC):
    @abstractmethod
    async def search(self, query: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_history(self, symbol: str, period: str, interval: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_company_profile(self, symbol: str) -> dict[str, Any]: ...


class RateLimiterPort(ABC):
    @abstractmethod
    async def acquire(self, key: str) -> RateLimitDecision: ...


class TelemetryPort(ABC):
    @abstractmethod
    def record(self, trace: InteractionTrace) -> None: ...


class GuardrailPort(ABC):
    @abstractmethod
    def inspect(self, text: str) -> None: ...
