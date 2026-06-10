import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.container import build_container
from app.api.error_handlers import register_error_handlers
from app.api.routes import chat, health
from app.application.ports import ChatModelPort, MarketDataPort
from app.settings import Settings


def create_app(
    settings: Settings | None = None,
    chat_model: ChatModelPort | None = None,
    market_data: MarketDataPort | None = None,
) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=settings.log_level.upper())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = build_container(settings, chat_model, market_data)
        yield
        await app.state.container.close()

    app = FastAPI(
        title="Finance Agent API",
        version="1.0.0",
        description="Conversational finance agent with per-conversation memory and "
        "Yahoo Finance tools",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    app.include_router(chat.router)
    app.include_router(health.router)
    register_error_handlers(app)
    return app


app = create_app()
