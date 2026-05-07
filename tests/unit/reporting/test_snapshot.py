from pathlib import Path

from doppel.judge.schema import Evaluation, Fact
from doppel.reporting.builder import ReportBuilder
from doppel.runtime.models import StepEvent
from doppel.runtime.orchestrator import RunResult
from doppel.sandbox.base import ResetResult


def test_report_markdown_snapshot_shape(tmp_path: Path) -> None:
    builder = ReportBuilder(tmp_path)
    result = RunResult(
        run_id="run-123",
        artifact_dir=tmp_path,
        mode="remote",
        step_count=1,
        reset_result=ResetResult(executed=False, strategy="none", detail="未配置 reset hook"),
        stop_reason="capture_only",
    )
    prompt_context = {
        "product": {
            "name": "PodFlow",
            "entry_url": "https://example.com",
            "description": "A podcast app",
        },
        "persona": {
            "id": "newcomer",
            "name": "Alex",
            "behavior_style": "Careful",
        },
        "skill": {
            "mission": "Find and play something.",
        },
    }
    steps = [
        StepEvent(
            step_id=1,
            timestamp="2026-04-10T18:00:00Z",
            url="https://example.com",
            page_title="Home",
            action_type="stop",
            action_input=None,
            target_description="初始视口截图",
            observation_summary="观察到页面「Home」，URL：https://example.com",
            reasoning_summary="Agent 决定停止：capture_only",
            screenshot_path="screenshots/step-001.png",
            elapsed_ms=120,
            status="stopped",
        )
    ]
    facts = [
        Fact(
            fact_id="fact_step_count",
            type="step_count",
            statement="本次运行记录了 1 个步骤。",
            evidence_step_ids=[1],
            confidence=1.0,
        )
    ]
    evaluations = [
        Evaluation(
            criterion_id="clarity",
            result="partial",
            summary="本次运行完成了证据捕获，但还没有执行完整任务路径。",
            evidence_fact_ids=["fact_step_count"],
            evidence_step_ids=[1],
        )
    ]

    report_md, _ = builder.write(
        run_result=result,
        prompt_context=prompt_context,
        steps=steps,
        facts=facts,
        evaluations=evaluations,
    )

    markdown = report_md.read_text(encoding="utf-8")
    assert "## 体验摩擦点" in markdown
    assert "还没有执行完整任务路径" in markdown
    assert "## 评审标准" in markdown
    assert "## 截图" in markdown
