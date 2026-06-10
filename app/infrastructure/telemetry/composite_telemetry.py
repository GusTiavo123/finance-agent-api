from collections.abc import Sequence

from app.application.ports import TelemetryPort
from app.domain.models import InteractionTrace


class CompositeTelemetry(TelemetryPort):
    def __init__(self, sinks: Sequence[TelemetryPort]):
        self._sinks = tuple(sinks)

    def record(self, trace: InteractionTrace) -> None:
        for sink in self._sinks:
            sink.record(trace)
