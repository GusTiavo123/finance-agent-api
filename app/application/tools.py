import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.application.ports import MarketDataPort
from app.domain.errors import MarketDataError
from app.domain.models import ToolSpec


@dataclass(frozen=True)
class AgentTool:
    spec: ToolSpec
    handler: Callable[[dict[str, Any]], Awaitable[str]]


class SearchArgs(BaseModel):
    query: str = Field(description="Company name or partial symbol, e.g. 'Mercado Libre'")


class QuoteArgs(BaseModel):
    symbol: str = Field(description="Ticker symbol, e.g. AAPL, MELI, BTC-USD")


class HistoryArgs(BaseModel):
    symbol: str = Field(description="Ticker symbol, e.g. AAPL, MELI, BTC-USD")
    period: Literal["5d", "1mo", "3mo", "6mo", "1y", "5y"] = Field(
        default="1mo", description="How far back to fetch prices"
    )
    interval: Literal["1d", "1wk", "1mo"] = Field(
        default="1d", description="Granularity of each data point"
    )


class ProfileArgs(BaseModel):
    symbol: str = Field(description="Ticker symbol, e.g. AAPL, MELI")


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _tool(
    name: str,
    description: str,
    args_model: type[BaseModel],
    run: Callable[[BaseModel], Awaitable[Any]],
) -> AgentTool:
    async def handler(arguments: dict[str, Any]) -> str:
        try:
            args = args_model.model_validate(arguments)
        except ValidationError as exc:
            return _dump({"error": f"Invalid arguments: {exc.errors(include_url=False)}"})
        try:
            return _dump(await run(args))
        except MarketDataError as exc:
            return _dump({"error": exc.message})

    schema = args_model.model_json_schema()
    schema.pop("title", None)
    return AgentTool(
        spec=ToolSpec(name=name, description=description, parameters=schema),
        handler=handler,
    )


def build_market_tools(market_data: MarketDataPort) -> tuple[AgentTool, ...]:
    return (
        _tool(
            "search_symbols",
            "Search ticker symbols by company name. Use it whenever the user mentions a "
            "company without an explicit ticker.",
            SearchArgs,
            lambda args: market_data.search(args.query),
        ),
        _tool(
            "get_stock_quote",
            "Get the latest market snapshot for a ticker: price, currency, daily change, "
            "ranges and market cap.",
            QuoteArgs,
            lambda args: market_data.get_quote(args.symbol),
        ),
        _tool(
            "get_historical_prices",
            "Get historical OHLCV prices for a ticker over a period. Useful for trends, "
            "performance and comparisons over time.",
            HistoryArgs,
            lambda args: market_data.get_history(args.symbol, args.period, args.interval),
        ),
        _tool(
            "get_company_profile",
            "Get company information for a ticker: name, sector, industry, country and a "
            "short business summary.",
            ProfileArgs,
            lambda args: market_data.get_company_profile(args.symbol),
        ),
    )
