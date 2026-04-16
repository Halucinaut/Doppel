from __future__ import annotations

import json
from pathlib import Path

from doppel.config.models import JudgeCriterion
from doppel.judge.schema import Evaluation, Fact


class CriteriaEvaluator:
    def evaluate(self, *, criteria: list[JudgeCriterion], facts: list[Fact]) -> list[Evaluation]:
        step_count = _step_count_from_facts(facts)
        stop_reason = _stop_reason_from_facts(facts)
        evaluations = []

        for criterion in criteria:
            result, summary = self._evaluate_single(criterion, step_count=step_count, stop_reason=stop_reason)
            evaluations.append(
                Evaluation(
                    criterion_id=criterion.id,
                    result=result,
                    summary=summary,
                    evidence_fact_ids=[fact.fact_id for fact in facts[:2]],
                    evidence_step_ids=_collect_step_ids(facts),
                )
            )
        return evaluations

    def write(self, artifact_dir: Path, evaluations: list[Evaluation]) -> Path:
        path = artifact_dir / "evaluation.json"
        path.write_text(
            json.dumps([evaluation.model_dump(mode="json") for evaluation in evaluations], indent=2),
            encoding="utf-8",
        )
        return path

    def _evaluate_single(self, criterion: JudgeCriterion, *, step_count: int, stop_reason: str) -> tuple[str, str]:
        normalized = criterion.id.lower()
        if "path" in normalized or "efficiency" in normalized:
            if step_count <= 5:
                return "pass", f"Reached the current stopping point in {step_count} steps."
            if step_count <= 8:
                return "partial", f"Needed {step_count} steps, which is acceptable but not efficient."
            return "fail", f"Needed {step_count} steps, indicating a long or unclear path."

        if stop_reason == "mission_completed":
            return "pass", "The run ended with mission completion."
        if stop_reason in {"capture_only", "prepared"}:
            return "partial", "The run captured evidence but did not execute a full task path."
        return "fail", f"The run ended with stop reason '{stop_reason}'."


def _step_count_from_facts(facts: list[Fact]) -> int:
    for fact in facts:
        if fact.fact_id == "fact_step_count":
            return int(fact.statement.split()[2])
    return 0


def _stop_reason_from_facts(facts: list[Fact]) -> str:
    for fact in facts:
        if fact.fact_id == "fact_stop_reason":
            return fact.statement.split("'")[1]
    return "unknown"


def _collect_step_ids(facts: list[Fact]) -> list[int]:
    seen: list[int] = []
    for fact in facts:
        for step_id in fact.evidence_step_ids:
            if step_id not in seen:
                seen.append(step_id)
    return seen
