class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ConversationNotFoundError(DomainError):
    code = "conversation_not_found"

    def __init__(self, conversation_id: str):
        super().__init__(f"Conversation '{conversation_id}' does not exist")
        self.conversation_id = conversation_id


class RateLimitExceededError(DomainError):
    code = "rate_limit_exceeded"

    def __init__(self, retry_after_seconds: int, limit: int, remaining: int):
        super().__init__("Rate limit exceeded, slow down and retry later")
        self.retry_after_seconds = retry_after_seconds
        self.limit = limit
        self.remaining = remaining


class GuardrailViolationError(DomainError):
    code = "input_rejected"

    def __init__(self, reason: str):
        super().__init__(f"Message rejected by input guardrail: {reason}")
        self.reason = reason


class MarketDataError(DomainError):
    code = "market_data_error"


class AgentExecutionError(DomainError):
    code = "agent_execution_error"
