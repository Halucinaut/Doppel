from pathlib import Path

from doppel.browser.adapter import StubBrowserAdapter
from doppel.config.loader import build_run_spec
from doppel.runtime.agent_runtime import AgentRuntime
from doppel.runtime.models import Action, PerceptionInput
from doppel.sandbox.remote import RemoteUrlSandbox
from doppel.session.recorder import SessionRecorder


def _write_minimal_files(tmp_path: Path) -> tuple[Path, Path]:
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "PodFlow"',
                'entry_url: "https://example.com"',
                'description: "A podcast app"',
            ]
        ),
        encoding="utf-8",
    )
    skill = tmp_path / "skill.yaml"
    skill.write_text(
        "\n".join(
            [
                'name: "Discovery"',
                'version: "1.0"',
                'persona: "newcomer"',
                'mission: "Find and play something."',
                "stop_conditions:",
                '  - "Audio is playing"',
                "judge_criteria:",
                '  - id: "path_efficiency"',
                '    question: "How direct was the path?"',
                '    good: "Reached quickly"',
                '    bad: "Got lost"',
            ]
        ),
        encoding="utf-8",
    )
    return product, skill


def test_agent_runtime_runs_a_visual_first_smoke_loop(tmp_path: Path) -> None:
    product, skill = _write_minimal_files(tmp_path)
    spec = build_run_spec(product, skill)
    sandbox = RemoteUrlSandbox(artifact_root=tmp_path / ".doppel" / "runs")
    ctx = sandbox.prepare(spec)
    recorder = SessionRecorder(ctx.artifact_dir)
    adapter = StubBrowserAdapter()
    seen = {"count": 0}

    def decide(perception: PerceptionInput) -> Action:
        seen["count"] += 1
        if seen["count"] == 1:
            return Action(action_type="click", target_description="Start free button in top-right")
        return Action(action_type="stop", stop_reason="mission_completed", target_description="Playback started")

    runtime = AgentRuntime(adapter=adapter, decide=decide)
    result = runtime.run(spec, ctx, recorder)
    session_path = recorder.write_session()

    assert result.step_count == 2
    assert result.stop_reason == "mission_completed"
    assert len(result.steps) == 2
    assert adapter.actions[0].target_description == "Start free button in top-right"
    assert session_path.exists()
    assert (ctx.artifact_dir / "screenshots" / "step-001.png").exists()
    assert (ctx.artifact_dir / "screenshots" / "step-002.png").exists()
