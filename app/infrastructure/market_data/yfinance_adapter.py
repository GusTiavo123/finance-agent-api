import asyncio
import math
from typing import Any

import yfinance as yf

from app.application.ports import MarketDataPort
from app.domain.errors import MarketDataError

MAX_HISTORY_ROWS = 60
SUMMARY_CHARS = 600


class YFinanceMarketData(MarketDataPort):
    async def search(self, query: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._search, query)

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._quote, symbol)

    async def get_history(self, symbol: str, period: str, interval: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._history, symbol, period, interval)

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._profile, symbol)

    def _search(self, query: str) -> list[dict[str, Any]]:
        try:
            quotes = yf.Search(
                query, max_results=5, news_count=0, enable_fuzzy_query=True
            ).quotes
        except Exception as exc:
            raise MarketDataError(f"Symbol search failed for '{query}': {exc}") from exc
        if not quotes:
            raise MarketDataError(f"No symbols found for '{query}'")
        return [
            {
                "symbol": item.get("symbol"),
                "name": item.get("shortname") or item.get("longname"),
                "exchange": item.get("exchDisp") or item.get("exchange"),
                "type": item.get("quoteType"),
            }
            for item in quotes
        ]

    def _quote(self, symbol: str) -> dict[str, Any]:
        info = self._fast_info(symbol)
        price = _number(info, "lastPrice")
        previous_close = _number(info, "previousClose")
        change_percent = None
        if price is not None and previous_close:
            change_percent = round((price - previous_close) / previous_close * 100, 2)
        return {
            "symbol": symbol.upper(),
            "currency": info.get("currency"),
            "price": price,
            "previous_close": previous_close,
            "change_percent": change_percent,
            "day_low": _number(info, "dayLow"),
            "day_high": _number(info, "dayHigh"),
            "year_low": _number(info, "yearLow"),
            "year_high": _number(info, "yearHigh"),
            "market_cap": _number(info, "marketCap"),
        }

    def _history(self, symbol: str, period: str, interval: str) -> dict[str, Any]:
        try:
            frame = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        except Exception as exc:
            raise MarketDataError(f"History lookup failed for '{symbol}': {exc}") from exc
        if frame.empty:
            raise MarketDataError(f"No price history found for '{symbol}'")
        frame = frame.tail(MAX_HISTORY_ROWS)
        candles = [
            {
                "date": index.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            }
            for index, row in frame.iterrows()
        ]
        first_close, last_close = candles[0]["close"], candles[-1]["close"]
        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "change_percent": round((last_close - first_close) / first_close * 100, 2)
            if first_close
            else None,
            "candles": candles,
        }

    def _profile(self, symbol: str) -> dict[str, Any]:
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception as exc:
            raise MarketDataError(f"Profile lookup failed for '{symbol}': {exc}") from exc
        name = info.get("longName") or info.get("shortName")
        if not name:
            raise MarketDataError(f"No company profile found for '{symbol}'")
        summary = info.get("longBusinessSummary") or ""
        return {
            "symbol": symbol.upper(),
            "name": name,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees"),
            "summary": summary[:SUMMARY_CHARS],
        }

    def _fast_info(self, symbol: str) -> dict[str, Any]:
        try:
            info = dict(yf.Ticker(symbol).fast_info)
        except Exception as exc:
            raise MarketDataError(f"Quote lookup failed for '{symbol}': {exc}") from exc
        if _number(info, "lastPrice") is None:
            raise MarketDataError(f"No quote found for '{symbol}'")
        return info


def _number(data: dict[str, Any], key: str) -> float | None:
    value = data.get(key)
    if value is None or not isinstance(value, (int, float)) or math.isnan(value):
        return None
    return round(float(value), 4)
