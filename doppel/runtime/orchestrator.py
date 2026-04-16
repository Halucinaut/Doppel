from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doppel.browser.adapter import StubBrowserAdapter
from doppel.browser.browser_use_client import run_browser_use_agent
from doppel.browser.playwright_adapter import PlaywrightBrowserAdapter
from doppel.config.loader import build_run_spec
from doppel.config.models import RunSpec
from doppel.judge.criteria_evaluator import CriteriaEvaluator
from doppel.judge.fact_extractor import FactExtractor
from doppel.reporting.builder import ReportBuilder
from doppel.runtime.agent_runtime import AgentRuntime
from doppel.runtime.models import Action, PerceptionInput
from doppel.sandbox.base import ResetResult, SandboxContext
from doppel.sandbox.preview import LocalPreviewSandbox
from doppel.sandbox.remote import RemoteUrlSandbox
from doppel.session.recorder import SessionRecorder, normalize_for_json


@dataclass(slots=True)
class RunResult:
    run_id: str
    artifact_dir: Path
    mode: str
    step_count: int
    reset_result: ResetResult
    stop_reason: str
    error_message: str | None = None
    report_path: Path | None = None
    report_json_path: Path | None = None


def run_pipeline(
    *,
    product_path: Path,
    skill_path: Path,
    personas_path: Path | None = None,
    runtime_config_path: Path | None = None,
    artifact_root: Path | None = None,
    use_real_browser: bool = False,
    decision_provider: str = "capture-only",
    show_browser: bool = False,
) -> RunResult:
    artifact_root = artifact_root or (product_path.resolve().parent / "output")
    spec = build_run_spec(
        product_path=product_path,
        skill_path=skill_path,
        personas_path=personas_path,
        runtime_config_path=runtime_config_path,
    )
    sandbox = _build_sandbox(spec, artifact_root)
    ctx = sandbox.prepare(spec)
    reset_result = sandbox.reset(ctx)
    recorder = SessionRecorder(ctx.artifact_dir)
    prompt_context = _build_prompt_context(spec)
    steps = []
    stop_reason = "prepared"
    errors = None
    facts = []
    evaluations = []
    try:
        runtime_result = _run_runtime(
            spec=spec,
            ctx=ctx,
            recorder=recorder,
            use_real_browser=use_real_browser,
            decision_provider=decision_provider,
            show_browser=show_browser,
        )
        steps = runtime_result.steps
        stop_reason = runtime_result.stop_reason
        facts = FactExtractor().extract(steps=steps, stop_reason=stop_reason)
        FactExtractor().write(ctx.artifact_dir, facts)
        evaluations = CriteriaEvaluator().evaluate(criteria=spec.skill.judge_criteria, facts=facts)
        CriteriaEvaluator().write(ctx.artifact_dir, evaluations)
    except Exception as exc:
        errors = {"message": str(exc), "type": exc.__class__.__name__}
        recorder.write_errors(errors)
        stop_reason = "runtime_error"
    recorder.write_run_meta(
        ctx,
        extra={
            "reset": normalize_for_json(reset_result),
            "stop_reason": stop_reason,
            "errors": errors,
            "use_real_browser": use_real_browser,
            "decision_provider": decision_provider,
            "show_browser": show_browser,
        },
    )
    recorder.write_prompt_context(prompt_context)
    recorder.write_session()
    run_result = RunResult(
        run_id=ctx.run_id,
        artifact_dir=ctx.artifact_dir,
        mode=ctx.mode,
        step_count=recorder.step_count,
        reset_result=reset_result,
        stop_reason=stop_reason,
        error_message=errors["message"] if errors else None,
    )
    report_path, report_json_path = ReportBuilder(ctx.artifact_dir).write(
        run_result=run_result,
        prompt_context=prompt_context,
        steps=steps,
        facts=facts,
        evaluations=evaluations,
    )
    sandbox.teardown(ctx)
    run_result.report_path = report_path
    run_result.report_json_path = report_json_path
    return run_result


def _build_sandbox(spec: RunSpec, artifact_root: Path | None) -> RemoteUrlSandbox | LocalPreviewSandbox:
    if spec.product.sandbox.mode == "local_preview":
        return LocalPreviewSandbox(artifact_root=artifact_root)
    return RemoteUrlSandbox(artifact_root=artifact_root)


def _build_prompt_context(spec: RunSpec) -> dict[str, object]:
    return {
        "product": {
            "name": spec.product.name,
            "entry_url": str(spec.product.entry_url),
            "description": spec.product.description,
        },
        "persona": spec.persona.model_dump(mode="json"),
        "skill": {
            "name": spec.skill.name,
            "mission": spec.skill.mission,
            "stop_conditions": spec.skill.stop_conditions,
            "judge_criteria": [criterion.model_dump(mode="json") for criterion in spec.skill.judge_criteria],
        },
    }


def _run_runtime(
    *,
    spec: RunSpec,
    ctx: SandboxContext,
    recorder: SessionRecorder,
    use_real_browser: bool,
    decision_provider: str,
    show_browser: bool,
):
    if decision_provider == "browser-use":
        runtime_result = run_browser_use_agent(
            spec=spec,
            ctx=ctx,
            project_root=Path.cwd(),
            show_browser=show_browser,
        )
        for step in runtime_result.steps:
            recorder.record_step(step)
        return runtime_result
    adapter = _build_browser_adapter(use_real_browser=use_real_browser, show_browser=show_browser)
    runtime = AgentRuntime(adapter=adapter, decide=_capture_only_decide)
    return runtime.run(spec, ctx, recorder)


def _build_browser_adapter(*, use_real_browser: bool, show_browser: bool):
    if use_real_browser:
        return PlaywrightBrowserAdapter(
            project_root=Path.cwd(),
            headless=not show_browser,
            slow_mo_ms=250 if show_browser else 0,
        )
    return StubBrowserAdapter()


def _capture_only_decide(_perception: PerceptionInput) -> Action:
    return Action(
        action_type="stop",
        stop_reason="capture_only",
        target_description="initial viewport capture",
    )
