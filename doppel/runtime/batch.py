from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doppel.runtime.orchestrator import RunResult, run_pipeline

RETRYABLE_STOP_REASONS = {"runtime_error", "browser_use_error", "agent_done_unsuccessful"}


@dataclass(slots=True)
class BatchRunItem:
    skill_path: Path
    attempts: list[RunResult]

    @property
    def final_result(self) -> RunResult:
        return self.attempts[-1]


@dataclass(slots=True)
class BatchRunResult:
    artifact_root: Path
    items: list[BatchRunItem]
    summary_json_path: Path
    summary_md_path: Path


def run_batch(
    *,
    product_path: Path,
    skill_paths: list[Path],
    personas_path: Path | None = None,
    runtime_config_path: Path | None = None,
    artifact_root: Path | None = None,
    use_real_browser: bool = False,
    decision_provider: str = "capture-only",
    show_browser: bool = False,
    retries: int = 1,
) -> BatchRunResult:
    resolved_artifact_root = (artifact_root or (product_path.resolve().parent / "output")).resolve()
    resolved_artifact_root.mkdir(parents=True, exist_ok=True)
    items: list[BatchRunItem] = []
    for skill_path in skill_paths:
        attempts: list[RunResult] = []
        for attempt in range(retries + 1):
            result = run_pipeline(
                product_path=product_path,
                skill_path=skill_path,
                personas_path=personas_path,
                runtime_config_path=runtime_config_path,
                artifact_root=resolved_artifact_root,
                use_real_browser=use_real_browser,
                decision_provider=decision_provider,
                show_browser=show_browser,
            )
            attempts.append(result)
            if not _should_retry(result) or attempt >= retries:
                break
        items.append(BatchRunItem(skill_path=skill_path, attempts=attempts))

    payload = _build_batch_payload(items)
    summary_json_path = resolved_artifact_root / "batch_summary.json"
    summary_md_path = resolved_artifact_root / "batch_report.md"
    summary_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_md_path.write_text(_build_batch_markdown(payload), encoding="utf-8")
    return BatchRunResult(
        artifact_root=resolved_artifact_root,
        items=items,
        summary_json_path=summary_json_path,
        summary_md_path=summary_md_path,
    )


def _should_retry(result: RunResult) -> bool:
    if result.stop_reason in RETRYABLE_STOP_REASONS:
        return True
    if result.step_count == 0:
        return True
    return False


def _build_batch_payload(items: list[BatchRunItem]) -> dict[str, Any]:
    runs = []
    for item in items:
        final = item.final_result
        report = _read_json(final.report_json_path)
        prompt_context = report.get("persona", {})
        evaluations = report.get("evaluations", [])
        runs.append(
            {
                "skill_path": str(item.skill_path),
                "attempt_count": len(item.attempts),
                "run_id": final.run_id,
                "persona_id": prompt_context.get("id"),
                "persona_name": prompt_context.get("name"),
                "artifact_dir": str(final.artifact_dir),
                "stop_reason": final.stop_reason,
                "step_count": final.step_count,
                "report_path": str(final.report_path) if final.report_path else None,
                "evaluation": [
                    {
                        "criterion_id": item["criterion_id"],
                        "result": item["result"],
                        "summary": item["summary"],
                    }
                    for item in evaluations
                ],
            }
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_count": len(runs),
        "runs": runs,
    }


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _build_batch_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Doppel 批量评测报告",
        "",
        f"- 生成时间：`{payload['generated_at']}`",
        f"- 运行数量：`{payload['run_count']}`",
        "",
        "## 汇总",
        "",
        "| Persona | Stop reason | Steps | Report |",
        "| --- | --- | ---: | --- |",
    ]
    for run in payload["runs"]:
        lines.append(
            f"| {run.get('persona_name') or run.get('persona_id') or '-'} "
            f"| `{run['stop_reason']}` "
            f"| {run['step_count']} "
            f"| `{run['report_path']}` |"
        )
    lines.extend(["", "## 分项结论"])
    for run in payload["runs"]:
        lines.extend(
            [
                "",
                f"### {run.get('persona_name') or run.get('persona_id') or run['run_id']}",
                "",
                f"- 产物目录：`{run['artifact_dir']}`",
                f"- 停止原因：`{run['stop_reason']}`",
                f"- 尝试次数：`{run['attempt_count']}`",
            ]
        )
        for evaluation in run["evaluation"]:
            lines.append(
                f"- `{evaluation['criterion_id']}`: `{evaluation['result']}` - {evaluation['summary']}"
            )
    return "\n".join(lines) + "\n"
