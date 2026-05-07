import pytest
from pydantic import ValidationError

from doppel.runtime.models import Action, StepEvent


def test_input_action_requires_text() -> None:
    with pytest.raises(ValidationError, match="input action requires text"):
        Action(action_type="input")


def test_stop_action_requires_reason() -> None:
    with pytest.raises(ValidationError, match="stop action requires stop_reason"):
        Action(action_type="stop")


def test_step_event_accepts_visual_target_description() -> None:
    event = StepEvent(
        step_id=1,
        timestamp="2026-04-10T18:00:00Z",
        url="https://example.com",
        page_title="Home",
        action_type="click",
        action_input=None,
        target_description="Start free button in top-right",
        observation_summary="The page shows a large hero and one clear CTA.",
        reasoning_summary="The top-right CTA appears to be the primary entry point.",
        screenshot_path="screenshots/step-001.png",
        elapsed_ms=1200,
        status="ok",
    )

    assert event.target_description == "Start free button in top-right"
    assert event.status == "ok"
