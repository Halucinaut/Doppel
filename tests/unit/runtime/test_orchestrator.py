import json
from pathlib import Path

from doppel.runtime.orchestrator import run_pipeline


def _write_minimal_files(tmp_path: Path) -> tuple[Path, Path]:
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "PodFlow"',
                'entry_url: "https://example.com"',
                'description: "A podcast app"',
                "sandbox:",
                '  mode: "remote"',
                '  seed_state: "new_user"',
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


def test_run_pipeline_writes_initial_artifacts(tmp_path: Path) -> None:
    product, skill = _write_minimal_files(tmp_path)

    result = run_pipeline(
        product_path=product,
        skill_path=skill,
        artifact_root=tmp_path / ".doppel" / "runs",
    )

    assert result.step_count == 1
    assert result.stop_reason == "capture_only"
    assert (result.artifact_dir / "run_meta.json").exists()
    assert (result.artifact_dir / "prompt_context.json").exists()
    assert (result.artifact_dir / "session.json").exists()
    assert (result.artifact_dir / "facts.json").exists()
    assert (result.artifact_dir / "evaluation.json").exists()
    assert (result.artifact_dir / "report.md").exists()
    assert (result.artifact_dir / "report.json").exists()
    assert (result.artifact_dir / "screenshots").exists()

    prompt_context = json.loads((result.artifact_dir / "prompt_context.json").read_text(encoding="utf-8"))
    assert prompt_context["persona"]["id"] == "newcomer"
    assert prompt_context["product"]["name"] == "PodFlow"
    session = json.loads((result.artifact_dir / "session.json").read_text(encoding="utf-8"))
    assert len(session) == 1
    assert session[0]["status"] == "stopped"
    evaluation = json.loads((result.artifact_dir / "evaluation.json").read_text(encoding="utf-8"))
    assert evaluation[0]["criterion_id"] == "path_efficiency"


def test_run_pipeline_defaults_output_to_product_sibling_output_dir(tmp_path: Path) -> None:
    example_dir = tmp_path / "examples" / "sample"
    example_dir.mkdir(parents=True)
    product, skill = _write_minimal_files(example_dir)

    result = run_pipeline(
        product_path=product,
        skill_path=skill,
    )

    assert result.artifact_dir.parent == (example_dir / "output").resolve()
    assert result.artifact_dir.name.startswith("podflow-")
