from fastapi import APIRouter, Depends

from app.api.container import Container
from app.api.security import get_container

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(container: Container = Depends(get_container)) -> dict:
    status = {"status": "ok", "storage": container.settings.storage_backend}
    if container.redis is not None:
        try:
            await container.redis.ping()
            status["redis"] = "up"
        except Exception:
            status["status"] = "degraded"
            status["redis"] = "down"
    return status
