from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_keys: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_timeout_seconds: int = 60

    storage_backend: Literal["redis", "memory"] = "redis"
    redis_url: str = "redis://localhost:6379/0"
    conversation_ttl_seconds: int = 60 * 60 * 24 * 7

    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

    max_agent_iterations: int = 5
    history_window_messages: int = 20

    telemetry_backends: str = "log"
    telemetry_file: str = "data/governance.jsonl"

    log_level: str = "INFO"

    @property
    def api_key_list(self) -> list[str]:
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]

    @property
    def telemetry_backend_list(self) -> list[str]:
        backends = self.telemetry_backends.split(",")
        return [backend.strip() for backend in backends if backend.strip()]
