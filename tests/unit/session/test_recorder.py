import json
from pathlib import Path

from doppel.runtime.models import StepEvent
from doppel.session.recorder import SessionRecorder


def test_session_recorder_writes_session_json(tmp_path: Path) -> None:
    recorder = SessionRecorder(tmp_path / "run-1")
    source_screenshot = tmp_path / "source-step.png"
    source_screenshot.write_bytes(b"fake-png")
    step = StepEvent(
        step_id=1,
        timestamp="2026-04-10T18:00:00Z",
        url="https://example.com",
        page_title="Home",
        action_type="click",
        action_input=None,
        target_description="Start free button",
        observation_summary="One clear CTA is visible.",
        reasoning_summary="The CTA seems like the primary action.",
        screenshot_path=str(source_screenshot),
        elapsed_ms=100,
        status="ok",
    )

    recorder.record_step(step)
    session_path = recorder.write_session()

    payload = json.loads(session_path.read_text(encoding="utf-8"))
    assert payload[0]["target_description"] == "Start free button"
    assert payload[0]["screenshot_path"].endswith("screenshots/step-001.png")
    assert (tmp_path / "run-1" / "screenshots" / "step-001.png").exists()
    assert recorder.step_count == 1
