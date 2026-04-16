from __future__ import annotations

import json
from pathlib import Path

from doppel.judge.schema import Fact
from doppel.runtime.models import StepEvent


class FactExtractor:
    def extract(self, *, steps: list[StepEvent], stop_reason: str) -> list[Fact]:
        step_ids = [step.step_id for step in steps]
        screenshot_count = len([step for step in steps if step.screenshot_path])
        facts = [
            Fact(
                fact_id="fact_step_count",
                type="step_count",
                statement=f"User completed {len(steps)} steps in this run.",
                evidence_step_ids=step_ids,
                confidence=1.0,
            ),
            Fact(
                fact_id="fact_stop_reason",
                type="stop_reason",
                statement=f"Run stopped because '{stop_reason}'.",
                evidence_step_ids=step_ids[-1:] if step_ids else [],
                confidence=1.0,
            ),
            Fact(
                fact_id="fact_screenshot_count",
                type="screenshot_count",
                statement=f"{screenshot_count} screenshots were captured.",
                evidence_step_ids=step_ids,
                confidence=1.0,
            ),
        ]
        if steps:
            facts.append(
                Fact(
                    fact_id="fact_last_action",
                    type="last_action",
                    statement=f"The last recorded action was '{steps[-1].action_type}'.",
                    evidence_step_ids=[steps[-1].step_id],
                    confidence=1.0,
                )
            )
        return facts

    def write(self, artifact_dir: Path, facts: list[Fact]) -> Path:
        path = artifact_dir / "facts.json"
        path.write_text(json.dumps([fact.model_dump(mode="json") for fact in facts], indent=2), encoding="utf-8")
        return path
