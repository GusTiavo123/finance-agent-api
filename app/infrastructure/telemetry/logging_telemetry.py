import json
import logging
from dataclasses import asdict

from app.application.ports import TelemetryPort
from app.domain.models import InteractionTrace


class StructuredLogTelemetry(TelemetryPort):
    def __init__(self, logger_name: str = "agent.governance"):
        self._logger = logging.getLogger(logger_name)

    def record(self, trace: InteractionTrace) -> None:
        payload = asdict(trace)
        payload["created_at"] = trace.created_at.isoformat()
        payload["event"] = "agent_interaction"
        self._logger.info(json.dumps(payload, ensure_ascii=False, default=str))
