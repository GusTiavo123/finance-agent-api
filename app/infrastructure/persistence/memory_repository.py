from collections.abc import Sequence

from app.application.ports import ConversationRepository
from app.domain.models import Message


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self):
        self._conversations: dict[str, list[Message]] = {}

    async def get(self, conversation_id: str) -> list[Message] | None:
        messages = self._conversations.get(conversation_id)
        return list(messages) if messages is not None else None

    async def append(self, conversation_id: str, messages: Sequence[Message]) -> None:
        self._conversations.setdefault(conversation_id, []).extend(messages)
