from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from doppel.judge.schema import Evaluation, Fact
from doppel.runtime.models import StepEvent


class SupportsRunResult(Protocol):
    run_id: str
    artifact_dir: Path
    mode: str
    step_count: int
    reset_result: Any


class ReportBuilder:
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir

    def write(
        self,
        *,
        run_result: SupportsRunResult,
        prompt_context: dict[str, Any],
        steps: list[StepEvent],
        facts: list[Fact] | None = None,
        evaluations: list[Evaluation] | None = None,
    ) -> tuple[Path, Path]:
        report_json_path = self.artifact_dir / "report.json"
        report_md_path = self.artifact_dir / "report.md"
        summary = self._build_summary(
            run_result=run_result,
            prompt_context=prompt_context,
            steps=steps,
            facts=facts or [],
            evaluations=evaluations or [],
        )
        report_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        report_md_path.write_text(self._build_markdown(summary), encoding="utf-8")
        return report_md_path, report_json_path

    def _build_summary(
        self,
        *,
        run_result: SupportsRunResult,
        prompt_context: dict[str, Any],
        steps: list[StepEvent],
        facts: list[Fact],
        evaluations: list[Evaluation],
    ) -> dict[str, Any]:
        return {
            "run_id": run_result.run_id,
            "mode": run_result.mode,
            "artifact_dir": str(run_result.artifact_dir),
            "step_count": len(steps),
            "stop_reason": run_result.stop_reason,
            "reset": {
                "executed": run_result.reset_result.executed,
                "strategy": run_result.reset_result.strategy,
                "detail": run_result.reset_result.detail,
            },
            "product": prompt_context["product"],
            "persona": prompt_context["persona"],
            "skill": prompt_context["skill"],
            "outcome": {
                "status": "completed" if steps else "prepared",
                "last_action": steps[-1].action_type if steps else None,
                "last_target": steps[-1].target_description if steps else None,
            },
            "friction_points": self._build_friction_points(evaluations),
            "facts": [fact.model_dump(mode="json") for fact in facts],
            "evaluations": [evaluation.model_dump(mode="json") for evaluation in evaluations],
            "screenshots": [step.screenshot_path for step in steps if step.screenshot_path],
        }

    def _build_markdown(self, summary: dict[str, Any]) -> str:
        lines = [
            "# Doppel Report",
            "",
            "## Summary",
            f"- Run ID: `{summary['run_id']}`",
            f"- Mode: `{summary['mode']}`",
            f"- Step count: `{summary['step_count']}`",
            f"- Outcome: `{summary['outcome']['status']}`",
            f"- Stop Reason: `{summary['stop_reason']}`",
            "",
            "## Product",
            f"- Name: {summary['product']['name']}",
            f"- Entry URL: {summary['product']['entry_url']}",
            f"- Description: {summary['product']['description']}",
            "",
            "## Persona",
            f"- ID: {summary['persona']['id']}",
            f"- Name: {summary['persona']['name']}",
            f"- Behavior Style: {summary['persona']['behavior_style']}",
            "",
            "## Mission",
            summary["skill"]["mission"],
            "",
            "## Friction Points",
        ]

        friction_points = summary["friction_points"]
        if friction_points:
            lines.extend(f"- {item}" for item in friction_points)
        else:
            lines.append("- No major friction points detected in this run")

        lines.extend(
            [
                "",
                "## Reset",
                f"- Executed: `{summary['reset']['executed']}`",
                f"- Strategy: `{summary['reset']['strategy']}`",
                f"- Detail: {summary['reset']['detail']}",
                "",
                "## Criteria",
            ]
        )

        evaluations = summary["evaluations"]
        if evaluations:
            lines.extend(
                f"- `{item['criterion_id']}`: `{item['result']}` - {item['summary']}" for item in evaluations
            )
        else:
            lines.append("- No criteria evaluated yet")

        lines.extend(["", "## Facts"])

        facts = summary["facts"]
        if facts:
            lines.extend(f"- `{item['type']}`: {item['statement']}" for item in facts)
        else:
            lines.append("- No extracted facts yet")

        lines.extend(
            [
                "",
            "## Screenshots",
            ]
        )

        if summary["screenshots"]:
            lines.extend(f"- `{path}`" for path in summary["screenshots"])
        else:
            lines.append("- No screenshots captured yet")

        return "\n".join(lines) + "\n"

    def _build_friction_points(self, evaluations: list[Evaluation]) -> list[str]:
        points = [evaluation.summary for evaluation in evaluations if evaluation.result != "pass"]
        return points
