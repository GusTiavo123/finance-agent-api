from collections.abc import Sequence

from app.application.ports import ChatModelPort, MarketDataPort, TelemetryPort
from app.application.tools import AgentTool, build_market_tools
from app.domain.errors import MarketDataError
from app.domain.models import (
    InteractionTrace,
    Message,
    ModelReply,
    TokenUsage,
    ToolCall,
    ToolSpec,
)


class ScriptedChatModel(ChatModelPort):
    def __init__(self, replies: list[ModelReply]):
        self._replies = list(replies)
        self.calls: list[dict] = []

    @property
    def model_name(self) -> str:
        return "scripted:test-model"

    async def generate(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
        allow_tool_use: bool = True,
    ) -> ModelReply:
        self.calls.append(
            {"messages": list(messages), "tools": list(tools), "allow_tool_use": allow_tool_use}
        )
        if not self._replies:
            raise AssertionError("ScriptedChatModel ran out of replies")
        return self._replies.pop(0)


class FailingChatModel(ChatModelPort):
    def __init__(self, error: Exception):
        self._error = error

    @property
    def model_name(self) -> str:
        return "scripted:failing-model"

    async def generate(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
        allow_tool_use: bool = True,
    ) -> ModelReply:
        raise self._error


class FakeMarketData(MarketDataPort):
    async def search(self, query: str):
        return [{"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "EQUITY"}]

    async def get_quote(self, symbol: str):
        if symbol == "FAIL":
            raise MarketDataError("No quote found for 'FAIL'")
        return {"symbol": symbol.upper(), "price": 290.5, "currency": "USD"}

    async def get_history(self, symbol: str, period: str, interval: str):
        return {"symbol": symbol.upper(), "period": period, "candles": []}

    async def get_company_profile(self, symbol: str):
        return {"symbol": symbol.upper(), "name": "Apple Inc.", "sector": "Technology"}


class CapturingTelemetry(TelemetryPort):
    def __init__(self):
        self.traces: list[InteractionTrace] = []

    def record(self, trace: InteractionTrace) -> None:
        self.traces.append(trace)


def reply_with_text(text: str, input_tokens: int = 10, output_tokens: int = 5) -> ModelReply:
    return ModelReply(
        content=text,
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
    )


def reply_with_tool_call(
    name: str, arguments: dict, call_id: str = "call_1", input_tokens: int = 10
) -> ModelReply:
    return ModelReply(
        content="",
        tool_calls=(ToolCall(id=call_id, name=name, arguments=arguments),),
        usage=TokenUsage(input_tokens=input_tokens, output_tokens=5, total_tokens=input_tokens + 5),
    )


def market_tools() -> tuple[AgentTool, ...]:
    return build_market_tools(FakeMarketData())
