from collections.abc import Sequence

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.application.ports import ChatModelPort
from app.domain.errors import AgentExecutionError
from app.domain.models import Message, ModelReply, Role, TokenUsage, ToolCall, ToolSpec

MAX_RESPONSE_TOKENS = 4096


class ClaudeChatModel(ChatModelPort):
    def __init__(self, model: str, timeout_seconds: int = 60, max_retries: int = 2):
        self._model_name = model
        self._model = ChatAnthropic(
            model=model,
            timeout=timeout_seconds,
            max_retries=max_retries,
            max_tokens=MAX_RESPONSE_TOKENS,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
        allow_tool_use: bool = True,
    ) -> ModelReply:
        model = self._model
        if tools:
            payload = [_to_anthropic_tool(spec) for spec in tools]
            if allow_tool_use:
                model = model.bind_tools(payload)
            else:
                model = model.bind_tools(payload, tool_choice={"type": "none"})
        try:
            reply = await model.ainvoke([_to_langchain(message) for message in messages])
        except Exception as exc:
            raise AgentExecutionError(f"Language model call failed: {exc}") from exc
        return ModelReply(
            content=_text_content(reply),
            tool_calls=tuple(
                ToolCall(id=call["id"] or "", name=call["name"], arguments=call["args"])
                for call in reply.tool_calls
            ),
            usage=_usage(reply),
        )


def _to_anthropic_tool(spec: ToolSpec) -> dict:
    return {
        "name": spec.name,
        "description": spec.description,
        "input_schema": spec.parameters,
    }


def _to_langchain(message: Message) -> BaseMessage:
    if message.role is Role.SYSTEM:
        return SystemMessage(content=message.content)
    if message.role is Role.USER:
        return HumanMessage(content=message.content)
    if message.role is Role.TOOL:
        return ToolMessage(content=message.content, tool_call_id=message.tool_call_id or "")
    return AIMessage(
        content=message.content,
        tool_calls=[
            {"id": call.id, "name": call.name, "args": call.arguments}
            for call in message.tool_calls
        ],
    )


def _text_content(reply: AIMessage) -> str:
    if isinstance(reply.content, str):
        return reply.content
    parts = [
        block["text"]
        for block in reply.content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "".join(parts)


def _usage(reply: AIMessage) -> TokenUsage:
    metadata = reply.usage_metadata or {}
    return TokenUsage(
        input_tokens=metadata.get("input_tokens", 0),
        output_tokens=metadata.get("output_tokens", 0),
        total_tokens=metadata.get("total_tokens", 0),
    )
