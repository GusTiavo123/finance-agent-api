from dataclasses import dataclass

from redis.asyncio import Redis

from app.application.chat_service import ChatService
from app.application.ports import ChatModelPort, MarketDataPort, RateLimiterPort, TelemetryPort
from app.application.tools import build_market_tools
from app.infrastructure.guardrails.rule_based_guardrail import RuleBasedGuardrail
from app.infrastructure.llm.claude_chat_model import ClaudeChatModel
from app.infrastructure.market_data.yfinance_adapter import YFinanceMarketData
from app.infrastructure.persistence.memory_repository import InMemoryConversationRepository
from app.infrastructure.persistence.redis_repository import RedisConversationRepository
from app.infrastructure.rate_limit.memory_rate_limiter import InMemoryRateLimiter
from app.infrastructure.rate_limit.redis_rate_limiter import RedisRateLimiter
from app.infrastructure.telemetry.composite_telemetry import CompositeTelemetry
from app.infrastructure.telemetry.file_telemetry import JsonFileTelemetry
from app.infrastructure.telemetry.logging_telemetry import StructuredLogTelemetry
from app.settings import Settings


@dataclass
class Container:
    settings: Settings
    chat_service: ChatService
    rate_limiter: RateLimiterPort
    redis: Redis | None

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.aclose()


def build_container(
    settings: Settings,
    chat_model: ChatModelPort | None = None,
    market_data: MarketDataPort | None = None,
) -> Container:
    redis = Redis.from_url(settings.redis_url) if settings.storage_backend == "redis" else None

    if redis is not None:
        repository = RedisConversationRepository(redis, settings.conversation_ttl_seconds)
        rate_limiter: RateLimiterPort = RedisRateLimiter(
            redis, settings.rate_limit_requests, settings.rate_limit_window_seconds
        )
    else:
        repository = InMemoryConversationRepository()
        rate_limiter = InMemoryRateLimiter(
            settings.rate_limit_requests, settings.rate_limit_window_seconds
        )

    chat_service = ChatService(
        repository=repository,
        chat_model=chat_model
        or ClaudeChatModel(settings.llm_model, settings.llm_timeout_seconds),
        tools=build_market_tools(market_data or YFinanceMarketData()),
        guardrail=RuleBasedGuardrail(),
        telemetry=_build_telemetry(settings),
        max_iterations=settings.max_agent_iterations,
        history_window=settings.history_window_messages,
    )
    return Container(
        settings=settings, chat_service=chat_service, rate_limiter=rate_limiter, redis=redis
    )


def _build_telemetry(settings: Settings) -> TelemetryPort:
    sinks: list[TelemetryPort] = []
    for backend in settings.telemetry_backend_list:
        if backend == "log":
            sinks.append(StructuredLogTelemetry())
        elif backend == "file":
            sinks.append(JsonFileTelemetry(settings.telemetry_file))
        else:
            raise ValueError(f"Unknown telemetry backend '{backend}', expected 'log' or 'file'")
    if not sinks:
        sinks.append(StructuredLogTelemetry())
    return sinks[0] if len(sinks) == 1 else CompositeTelemetry(sinks)
