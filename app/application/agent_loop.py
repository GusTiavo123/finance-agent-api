import json
import time
from collections.abc import Sequence

from app.application.ports import ChatModelPort
from app.application.tools import AgentTool
from app.domain.models import (
    AgentResult,
    AgentStep,
    Message,
    Role,
    TokenUsage,
    ToolCall,
)

RESULT_PREVIEW_CHARS = 300


async def agent_loop(
    chat_model: ChatModelPort,
    messages: list[Message],
    tools: Sequence[AgentTool],
    max_iterations: int,
) -> AgentResult:
    registry = {tool.spec.name: tool for tool in tools}
    specs = tuple(tool.spec for tool in tools)
    transcript = list(messages)
    usage = TokenUsage()
    steps: list[AgentStep] = []

    for iteration in range(1, max_iterations + 1):
        reply = await chat_model.generate(transcript, specs)
        usage = usage + reply.usage

        if not reply.tool_calls:
            return AgentResult(
                content=reply.content, usage=usage, steps=tuple(steps), iterations=iteration
            )

        transcript.append(
            Message(role=Role.ASSISTANT, content=reply.content, tool_calls=reply.tool_calls)
        )
        for call in reply.tool_calls:
            result, duration_ms = await _execute(registry, call)
            steps.append(
                AgentStep(
                    iteration=iteration,
                    tool_name=call.name,
                    arguments=call.arguments,
                    result_preview=result[:RESULT_PREVIEW_CHARS],
                    duration_ms=duration_ms,
                )
            )
            transcript.append(Message(role=Role.TOOL, content=result, tool_call_id=call.id))

    final = await chat_model.generate(transcript, specs, allow_tool_use=False)
    usage = usage + final.usage
    return AgentResult(
        content=final.content, usage=usage, steps=tuple(steps), iterations=max_iterations + 1
    )


async def _execute(registry: dict[str, AgentTool], call: ToolCall) -> tuple[str, int]:
    started = time.monotonic()
    tool = registry.get(call.name)
    if tool is None:
        result = json.dumps({"error": f"Unknown tool '{call.name}'"})
    else:
        result = await tool.handler(call.arguments)
    return result, int((time.monotonic() - started) * 1000)
