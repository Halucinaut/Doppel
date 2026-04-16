from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Callable

from doppel.browser.adapter import BrowserAdapter
from doppel.config.models import RunSpec
from doppel.runtime.models import Action, PerceptionInput, StepEvent
from doppel.runtime.stop_conditions import evaluate_stop_conditions
from doppel.sandbox.base import SandboxContext
from doppel.session.recorder import SessionRecorder


DecisionFn = Callable[[PerceptionInput], Action]


@dataclass(slots=True)
class RuntimeResult:
    step_count: int
    stop_reason: str
    steps: list[StepEvent]


class AgentRuntime:
    def __init__(self, adapter: BrowserAdapter, decide: DecisionFn) -> None:
        self.adapter = adapter
        self.decide = decide

    def run(self, spec: RunSpec, ctx: SandboxContext, recorder: SessionRecorder) -> RuntimeResult:
        self.adapter.open(ctx.entry_url)
        step_count = 0
        runtime_seconds = 0
        history_summary: str | None = None
        stop_reason = "unknown"
        recorded_steps: list[StepEvent] = []

        while True:
            step_count += 1
            started = perf_counter()
            screenshot_path = recorder.screenshots_dir / f"step-{step_count:03d}.png"
            perception = self.adapter.observe(screenshot_path=screenshot_path, history_summary=history_summary)
            action = self.decide(perception)

            if action.action_type != "stop":
                self.adapter.execute(action)

            elapsed_ms = int((perf_counter() - started) * 1000)
            runtime_seconds += max(1, elapsed_ms // 1000)
            status = "stopped" if action.action_type == "stop" else "ok"
            stop_reason = action.stop_reason or "agent_requested_stop"
            step = StepEvent(
                step_id=step_count,
                timestamp=datetime.now(UTC).isoformat(),
                url=perception.url,
                page_title=perception.page_title,
                action_type=action.action_type,
                action_input=_build_action_input(action),
                target_description=action.target_description,
                observation_summary=_build_observation_summary(perception),
                reasoning_summary=_build_reasoning_summary(action),
                screenshot_path=perception.screenshot_path,
                elapsed_ms=elapsed_ms,
                status=status,
                error_message=None,
            )
            recorder.record_step(step)
            recorded_steps.append(step)

            decision = evaluate_stop_conditions(
                step_count=step_count,
                max_steps=spec.run_limits.max_steps,
                runtime_seconds=runtime_seconds,
                max_runtime_seconds=spec.run_limits.max_runtime_seconds,
                mission_completed=action.stop_reason == "mission_completed",
                unrecoverable_error=False,
            )
            history_summary = f"step={step_count}, last_action={action.action_type}, stop={decision.reason}"
            if action.action_type == "stop":
                break
            if decision.should_stop:
                stop_reason = decision.reason or stop_reason
                break

        self.adapter.close()
        return RuntimeResult(step_count=step_count, stop_reason=stop_reason, steps=recorded_steps)


def _build_action_input(action: Action) -> str | None:
    if action.text:
        return action.text
    if action.x is not None and action.y is not None:
        return f"{action.x},{action.y}"
    return None


def _build_observation_summary(perception: PerceptionInput) -> str:
    return f"Observed page {perception.page_title or 'unknown'} at {perception.url}"


def _build_reasoning_summary(action: Action) -> str:
    if action.action_type == "stop":
        return f"Agent decided to stop: {action.stop_reason}"
    return f"Agent selected action '{action.action_type}' targeting '{action.target_description or 'unspecified target'}'"
