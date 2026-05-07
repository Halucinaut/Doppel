from doppel.runtime.stop_conditions import evaluate_stop_conditions


def test_stop_when_mission_completed() -> None:
    decision = evaluate_stop_conditions(
        step_count=3,
        max_steps=10,
        runtime_seconds=15,
        max_runtime_seconds=60,
        mission_completed=True,
    )

    assert decision.should_stop is True
    assert decision.reason == "mission_completed"


def test_stop_when_max_steps_reached() -> None:
    decision = evaluate_stop_conditions(
        step_count=10,
        max_steps=10,
        runtime_seconds=15,
        max_runtime_seconds=60,
    )

    assert decision.should_stop is True
    assert decision.reason == "max_steps"


def test_continue_when_within_limits() -> None:
    decision = evaluate_stop_conditions(
        step_count=3,
        max_steps=10,
        runtime_seconds=15,
        max_runtime_seconds=60,
    )

    assert decision.should_stop is False
    assert decision.reason is None
