from __future__ import annotations

import json
import shutil
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from doppel.runtime.models import StepEvent
from doppel.sandbox.base import SandboxContext


class SessionRecorder:
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir
        self.screenshots_dir = artifact_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._steps: list[StepEvent] = []

    def record_step(self, step: StepEvent) -> None:
        screenshot_path = step.screenshot_path.strip()
        if screenshot_path:
            source = Path(screenshot_path)
            if source.exists():
                destination = (self.screenshots_dir / f"step-{step.step_id:03d}{source.suffix or '.png'}").resolve()
                if source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)
                step.screenshot_path = str(destination)
        self._steps.append(step)

    def write_run_meta(self, ctx: SandboxContext, extra: dict[str, Any] | None = None) -> Path:
        payload = {
            "run_id": ctx.run_id,
            "mode": ctx.mode,
            "entry_url": ctx.entry_url,
            "seed_state": ctx.seed_state,
            "artifact_dir": str(ctx.artifact_dir),
            "auth_required": ctx.auth_context.required,
        }
        if extra:
            payload.update(extra)
        path = self.artifact_dir / "run_meta.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def write_prompt_context(self, payload: dict[str, Any]) -> Path:
        path = self.artifact_dir / "prompt_context.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def write_session(self) -> Path:
        path = self.artifact_dir / "session.json"
        path.write_text(
            json.dumps([step.model_dump(mode="json") for step in self._steps], indent=2),
            encoding="utf-8",
        )
        return path

    def write_errors(self, payload: dict[str, Any]) -> Path:
        path = self.artifact_dir / "errors.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @property
    def step_count(self) -> int:
        return len(self._steps)


def normalize_for_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: normalize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_for_json(item) for item in value]
    return value
