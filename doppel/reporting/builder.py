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
        report_json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
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
            "# Doppel 评审报告",
            "",
            "## 概览",
            f"- 运行 ID：`{summary['run_id']}`",
            f"- 运行模式：`{summary['mode']}`",
            f"- 步骤数：`{summary['step_count']}`",
            f"- 结果状态：`{summary['outcome']['status']}`",
            f"- 停止原因：`{summary['stop_reason']}`",
            "",
            "## 产品",
            f"- 名称：{summary['product']['name']}",
            f"- 入口 URL：{summary['product']['entry_url']}",
            f"- 描述：{summary['product']['description']}",
            "",
            "## 用户画像",
            f"- ID：{summary['persona']['id']}",
            f"- 名称：{summary['persona']['name']}",
            f"- 行为风格：{summary['persona']['behavior_style']}",
            "",
            "## 任务",
            summary["skill"]["mission"],
            "",
            "## 体验摩擦点",
        ]

        friction_points = summary["friction_points"]
        if friction_points:
            lines.extend(f"- {item}" for item in friction_points)
        else:
            lines.append("- 本次运行未检测到明显体验摩擦点")

        lines.extend(
            [
                "",
                "## 重置",
                f"- 是否执行：`{summary['reset']['executed']}`",
                f"- 策略：`{summary['reset']['strategy']}`",
                f"- 详情：{summary['reset']['detail']}",
                "",
                "## 评审标准",
            ]
        )

        evaluations = summary["evaluations"]
        if evaluations:
            for item in evaluations:
                lines.append(f"- `{item['criterion_id']}`: `{item['result']}` - {item['summary']}")
                if item.get("key_milestone"):
                    lines.append(f"  关键里程碑：{item['key_milestone']}")
                if item.get("improvement_suggestion"):
                    lines.append(f"  改进建议：{item['improvement_suggestion']}")
                if item.get("evidence_screenshots"):
                    lines.append(f"  截图证据：{'，'.join(item['evidence_screenshots'])}")
        else:
            lines.append("- 暂无已评审标准")

        lines.extend(["", "## 事实"])

        facts = summary["facts"]
        if facts:
            lines.extend(f"- `{item['type']}`: {item['statement']}" for item in facts)
        else:
            lines.append("- 暂无提取事实")

        lines.extend(
            [
                "",
            "## 截图",
            ]
        )

        if summary["screenshots"]:
            lines.extend(f"- `{path}`" for path in summary["screenshots"])
        else:
            lines.append("- 暂无截图")

        return "\n".join(lines) + "\n"

    def _build_friction_points(self, evaluations: list[Evaluation]) -> list[str]:
        points = [evaluation.summary for evaluation in evaluations if evaluation.result != "pass"]
        return points
