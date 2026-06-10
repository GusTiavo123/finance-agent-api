from fastapi import APIRouter, Depends, Path, Request

from app.api.container import Container
from app.api.schemas import (
    CONVERSATION_ID_PATTERN,
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ErrorResponse,
    MessageResponse,
    UsageResponse,
)
from app.api.security import enforce_rate_limit, get_client_id, get_container

router = APIRouter(tags=["chat"])

ERROR_RESPONSES = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
}


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={**ERROR_RESPONSES, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    dependencies=[Depends(enforce_rate_limit)],
)
async def send_message(
    payload: ChatRequest,
    request: Request,
    client_id: str = Depends(get_client_id),
    container: Container = Depends(get_container),
) -> ChatResponse:
    result = await container.chat_service.send_message(
        client_id=client_id,
        conversation_id=payload.conversation_id,
        text=payload.message,
        request_id=request.state.request_id,
    )
    return ChatResponse(
        conversation_id=result.conversation_id,
        reply=result.reply,
        usage=UsageResponse(
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            total_tokens=result.usage.total_tokens,
        ),
    )


@router.get(
    "/chat/{conversation_id}",
    response_model=ConversationResponse,
    responses={**ERROR_RESPONSES, 404: {"model": ErrorResponse}},
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_history(
    conversation_id: str = Path(pattern=CONVERSATION_ID_PATTERN),
    client_id: str = Depends(get_client_id),
    container: Container = Depends(get_container),
) -> ConversationResponse:
    messages = await container.chat_service.get_history(client_id, conversation_id)
    return ConversationResponse(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(
                role=message.role.value, content=message.content, created_at=message.created_at
            )
            for message in messages
        ],
    )
