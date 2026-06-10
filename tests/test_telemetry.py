import json

from app.domain.models import AgentStep, InteractionTrace, TokenUsage
from app.infrastructure.telemetry.composite_telemetry import CompositeTelemetry
from app.infrastructure.telemetry.file_telemetry import JsonFileTelemetry
from tests.conftest import CapturingTelemetry


def make_trace(request_id: str = "req-1") -> InteractionTrace:
    return InteractionTrace(
        request_id=request_id,
        client_id="client-a",
        conversation_id="conv-1",
        model="scripted:test-model",
        status="ok",
        user_message="precio de AAPL?",
        assistant_reply="290.5 USD",
        usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
        iterations=2,
        steps=(
            AgentStep(
                iteration=1,
                tool_name="get_stock_quote",
                arguments={"symbol": "AAPL"},
                result_preview='{"price": 290.5}',
                duration_ms=12,
            ),
        ),
        latency_ms=850,
    )


def test_file_telemetry_appends_one_json_line_per_trace(tmp_path):
    path = tmp_path / "governance.jsonl"
    telemetry = JsonFileTelemetry(str(path))

    telemetry.record(make_trace("req-1"))
    telemetry.record(make_trace("req-2"))

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["event"] == "agent_interaction"
    assert first["request_id"] == "req-1"
    assert first["usage"]["total_tokens"] == 15
    assert first["steps"][0]["tool_name"] == "get_stock_quote"


def test_file_telemetry_creates_missing_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "governance.jsonl"

    JsonFileTelemetry(str(path)).record(make_trace())

    assert path.exists()


def test_composite_telemetry_fans_out_to_every_sink(tmp_path):
    path = tmp_path / "governance.jsonl"
    capturing = CapturingTelemetry()
    telemetry = CompositeTelemetry([JsonFileTelemetry(str(path)), capturing])

    telemetry.record(make_trace())

    assert len(capturing.traces) == 1
    assert path.exists()
