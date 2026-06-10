import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AgentExecutionError,
    ConversationNotFoundError,
    DomainError,
    GuardrailViolationError,
    RateLimitExceededError,
)

logger = logging.getLogger("api.errors")

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    ConversationNotFoundError: 404,
    GuardrailViolationError: 422,
    RateLimitExceededError: 429,
    AgentExecutionError: 502,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        status = STATUS_BY_ERROR.get(type(exc), 400)
        headers = {}
        message = exc.message
        if isinstance(exc, RateLimitExceededError):
            headers["Retry-After"] = str(exc.retry_after_seconds)
            headers["X-RateLimit-Limit"] = str(exc.limit)
            headers["X-RateLimit-Remaining"] = str(exc.remaining)
        if status >= 500:
            logger.error("request_id=%s %s", request.state.request_id, exc.message)
            message = "The agent could not process the request, please try again later"
        return JSONResponse(
            status_code=status,
            content={"error": {"code": exc.code, "message": message}},
            headers=headers,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {401: "missing_api_key", 403: "invalid_api_key"}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": codes.get(exc.status_code, "http_error"),
                    "message": str(exc.detail),
                }
            },
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ()))
        message = f"{location}: {first.get('msg', 'invalid request')}"
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("request_id=%s unhandled error", request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Unexpected error, please try again later",
                }
            },
        )
