import hashlib
import secrets

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import APIKeyHeader

from app.api.container import Container
from app.domain.errors import RateLimitExceededError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_container(request: Request) -> Container:
    return request.app.state.container


async def require_api_key(
    api_key: str | None = Depends(api_key_header),
    container: Container = Depends(get_container),
) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    valid_keys = container.settings.api_key_list
    candidate = api_key.encode("utf-8")
    if not valid_keys or not any(
        secrets.compare_digest(candidate, key.encode("utf-8")) for key in valid_keys
    ):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


async def get_client_id(api_key: str = Depends(require_api_key)) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


async def enforce_rate_limit(
    request: Request,
    response: Response,
    client_id: str = Depends(get_client_id),
    container: Container = Depends(get_container),
) -> None:
    decision = await container.rate_limiter.acquire(client_id)
    request.state.rate_limit = decision
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    if not decision.allowed:
        raise RateLimitExceededError(
            decision.retry_after_seconds, decision.limit, decision.remaining
        )
