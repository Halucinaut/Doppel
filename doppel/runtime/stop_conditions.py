from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StopDecision:
    should_stop: bool
    reason: str | None = None


def evaluate_stop_conditions(
    *,
    step_count: int,
    max_steps: int,
    runtime_seconds: int,
    max_runtime_seconds: int,
    mission_completed: bool = False,
    unrecoverable_error: bool = False,
) -> StopDecision:
    if mission_completed:
        return StopDecision(True, "mission_completed")
    if unrecoverable_error:
        return StopDecision(True, "unrecoverable_error")
    if step_count >= max_steps:
        return StopDecision(True, "max_steps")
    if runtime_seconds >= max_runtime_seconds:
        return StopDecision(True, "max_runtime_seconds")
    return StopDecision(False, None)
