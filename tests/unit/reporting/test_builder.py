import json
from pathlib import Path

from doppel.judge.schema import Evaluation, Fact
from doppel.reporting.builder import ReportBuilder
from doppel.runtime.models import StepEvent
from doppel.runtime.orchestrator import RunResult
from doppel.sandbox.base import ResetResult


def test_report_builder_writes_markdown_and_json(tmp_path: Path) -> None:
    builder = ReportBuilder(tmp_path)
    result = RunResult(
        run_id="run-123",
        artifact_dir=tmp_path,
        mode="remote",
        step_count=1,
        reset_result=ResetResult(executed=False, strategy="none", detail="未配置 reset hook"),
        stop_reason="mission_completed",
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
            action_type="click",
            action_input=None,
            target_description="Hero CTA",
            observation_summary="观察到页面「Home」，URL：https://example.com",
            reasoning_summary="Agent 选择动作「click」，目标：「Hero CTA」",
            screenshot_path="screenshots/step-001.png",
            elapsed_ms=120,
            status="ok",
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
            criterion_id="path_efficiency",
            result="pass",
            summary="当前停止点在 1 步内到达，路径较短。",
            evidence_fact_ids=["fact_step_count"],
            evidence_step_ids=[1],
            evidence_screenshots=["screenshots/step-001.png"],
            key_milestone="步骤 1 完成任务",
        )
    ]

    report_md, report_json = builder.write(
        run_result=result,
        prompt_context=prompt_context,
        steps=steps,
        facts=facts,
        evaluations=evaluations,
    )

    md = report_md.read_text(encoding="utf-8")
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    assert "# Doppel 评审报告" in md
    assert "PodFlow" in md
    assert "path_efficiency" in md
    assert payload["step_count"] == 1
    assert payload["stop_reason"] == "mission_completed"
    assert payload["screenshots"] == ["screenshots/step-001.png"]
    assert payload["evaluations"][0]["evidence_screenshots"] == ["screenshots/step-001.png"]
    assert payload["evaluations"][0]["key_milestone"] == "步骤 1 完成任务"


def test_report_builder_filters_empty_screenshot_paths(tmp_path: Path) -> None:
    builder = ReportBuilder(tmp_path)
    result = RunResult(
        run_id="run-456",
        artifact_dir=tmp_path,
        mode="remote",
        step_count=2,
        reset_result=ResetResult(executed=False, strategy="none", detail="未配置 reset hook"),
        stop_reason="mission_completed",
    )
    prompt_context = {
        "product": {"name": "Example Domain", "entry_url": "https://example.com", "description": "Example"},
        "persona": {"id": "newcomer", "name": "Alex", "behavior_style": "Careful"},
        "skill": {"mission": "Understand the page."},
    }
    steps = [
        StepEvent(
            step_id=1,
            timestamp="2026-04-10T18:00:00Z",
            url="https://example.com",
            page_title="Initial",
            action_type="wait",
            action_input=None,
            target_description="initial state",
            observation_summary="Initial observation",
            reasoning_summary="Start",
            screenshot_path="",
            elapsed_ms=0,
            status="ok",
        ),
        StepEvent(
            step_id=2,
            timestamp="2026-04-10T18:00:01Z",
            url="https://example.com",
            page_title="example.com",
            action_type="click",
            action_input=None,
            target_description="Learn more",
            observation_summary="Clicked main link",
            reasoning_summary="Proceed",
            screenshot_path="screenshots/step-002.png",
            elapsed_ms=100,
            status="ok",
        ),
    ]

    _, report_json = builder.write(
        run_result=result,
        prompt_context=prompt_context,
        steps=steps,
        facts=[],
        evaluations=[],
    )

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["screenshots"] == ["screenshots/step-002.png"]
