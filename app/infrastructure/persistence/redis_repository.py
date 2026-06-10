import json
from collections.abc import Sequence
from datetime import datetime

from redis.asyncio import Redis

from app.application.ports import ConversationRepository
from app.domain.models import Message, Role


class RedisConversationRepository(ConversationRepository):
    def __init__(self, redis: Redis, ttl_seconds: int):
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, conversation_id: str) -> list[Message] | None:
        raw = await self._redis.lrange(self._key(conversation_id), 0, -1)
        if not raw:
            return None
        return [_deserialize(item) for item in raw]

    async def append(self, conversation_id: str, messages: Sequence[Message]) -> None:
        key = self._key(conversation_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.rpush(key, *[_serialize(message) for message in messages])
            pipe.expire(key, self._ttl)
            await pipe.execute()

    @staticmethod
    def _key(conversation_id: str) -> str:
        return f"conversation:{conversation_id}"


def _serialize(message: Message) -> str:
    return json.dumps(
        {
            "role": message.role.value,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
        ensure_ascii=False,
    )


def _deserialize(raw: str | bytes) -> Message:
    data = json.loads(raw)
    return Message(
        role=Role(data["role"]),
        content=data["content"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )
