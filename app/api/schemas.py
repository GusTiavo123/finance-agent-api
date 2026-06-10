from datetime import datetime

from pydantic import BaseModel, Field

CONVERSATION_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(
        default=None,
        pattern=CONVERSATION_ID_PATTERN,
        description="Conversation thread id. Omit it to start a new conversation.",
    )
    message: str = Field(min_length=1, max_length=4000)


class UsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    usage: UsageResponse


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    conversation_id: str
    messages: list[MessageResponse]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
