import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.application.agent_loop import agent_loop
from app.application.ports import (
    ChatModelPort,
    ConversationRepository,
    GuardrailPort,
    TelemetryPort,
)
from app.application.prompts import SYSTEM_PROMPT
from app.application.tools import AgentTool
from app.domain.errors import ConversationNotFoundError, GuardrailViolationError
from app.domain.models import (
    AgentResult,
    InteractionTrace,
    Message,
    Role,
    TokenUsage,
)

TRACE_TEXT_CHARS = 500


@dataclass(frozen=True)
class ChatResult:
    conversation_id: str
    reply: str
    usage: TokenUsage


class ChatService:
    def __init__(
        self,
        repository: ConversationRepository,
        chat_model: ChatModelPort,
        tools: Sequence[AgentTool],
        guardrail: GuardrailPort,
        telemetry: TelemetryPort,
        max_iterations: int,
        history_window: int,
    ):
        self._repository = repository
        self._chat_model = chat_model
        self._tools = tools
        self._guardrail = guardrail
        self._telemetry = telemetry
        self._max_iterations = max_iterations
        self._history_window = history_window

    async def send_message(
        self, client_id: str, conversation_id: str | None, text: str, request_id: str
    ) -> ChatResult:
        started = time.monotonic()
        resolved_id = conversation_id or uuid.uuid4().hex

        try:
            self._guardrail.inspect(text)
        except GuardrailViolationError:
            self._record(
                request_id, client_id, resolved_id, "input_rejected", text, "", None, started
            )
            raise

        history = await self._repository.get(self._scoped(client_id, resolved_id)) or []
        user_message = Message(role=Role.USER, content=text)
        prompt = [
            Message(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            *self._window(history),
            user_message,
        ]

        try:
            result = await agent_loop(
                chat_model=self._chat_model,
                messages=prompt,
                tools=self._tools,
                max_iterations=self._max_iterations,
            )
        except Exception:
            self._record(request_id, client_id, resolved_id, "error", text, "", None, started)
            raise

        assistant_message = Message(role=Role.ASSISTANT, content=result.content)
        await self._repository.append(
            self._scoped(client_id, resolved_id), [user_message, assistant_message]
        )
        self._record(
            request_id, client_id, resolved_id, "ok", text, result.content, result, started
        )

        return ChatResult(conversation_id=resolved_id, reply=result.content, usage=result.usage)

    async def get_history(self, client_id: str, conversation_id: str) -> list[Message]:
        messages = await self._repository.get(self._scoped(client_id, conversation_id))
        if messages is None:
            raise ConversationNotFoundError(conversation_id)
        return messages

    def _window(self, history: list[Message]) -> list[Message]:
        window = history[-self._history_window :]
        while window and window[0].role is not Role.USER:
            window.pop(0)
        return window

    @staticmethod
    def _scoped(client_id: str, conversation_id: str) -> str:
        return f"{client_id}:{conversation_id}"

    def _record(
        self,
        request_id: str,
        client_id: str,
        conversation_id: str,
        status: str,
        user_text: str,
        reply: str,
        result: AgentResult | None,
        started: float,
    ) -> None:
        self._telemetry.record(
            InteractionTrace(
                request_id=request_id,
                client_id=client_id,
                conversation_id=conversation_id,
                model=self._chat_model.model_name,
                status=status,
                user_message=user_text[:TRACE_TEXT_CHARS],
                assistant_reply=reply[:TRACE_TEXT_CHARS],
                usage=result.usage if result else TokenUsage(),
                iterations=result.iterations if result else 0,
                steps=result.steps if result else (),
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        )
