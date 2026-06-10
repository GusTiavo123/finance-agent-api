import json
from dataclasses import asdict
from pathlib import Path

from app.application.ports import TelemetryPort
from app.domain.models import InteractionTrace


class JsonFileTelemetry(TelemetryPort):
    def __init__(self, file_path: str):
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, trace: InteractionTrace) -> None:
        payload = asdict(trace)
        payload["created_at"] = trace.created_at.isoformat()
        payload["event"] = "agent_interaction"
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
