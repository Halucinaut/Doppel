from pathlib import Path

import httpx
import pytest

from doppel.config.loader import build_run_spec
from doppel.sandbox.preview import LocalPreviewSandbox
from doppel.sandbox.remote import RemoteUrlSandbox


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


def test_remote_sandbox_prepare_creates_context(tmp_path: Path) -> None:
    product, skill = _write_minimal_files(tmp_path)
    spec = build_run_spec(product, skill)

    sandbox = RemoteUrlSandbox(artifact_root=tmp_path / ".doppel" / "runs")
    ctx = sandbox.prepare(spec)

    assert ctx.mode == "remote"
    assert ctx.entry_url == "https://example.com/"
    assert ctx.seed_state == "new_user"
    assert ctx.artifact_dir.exists()
    assert ctx.artifact_dir.parent == tmp_path / ".doppel" / "runs"
    assert ctx.artifact_dir.name.startswith("podflow-")


def test_local_preview_sandbox_prepare_creates_context(tmp_path: Path) -> None:
    product, skill = _write_minimal_files(tmp_path)
    spec = build_run_spec(product, skill)

    sandbox = LocalPreviewSandbox(artifact_root=tmp_path / ".doppel" / "runs")
    ctx = sandbox.prepare(spec)
    reset_result = sandbox.reset(ctx)

    assert ctx.mode == "local_preview"
    assert ctx.artifact_dir.exists()
    assert reset_result.executed is False
    assert reset_result.strategy == "none"


def test_remote_sandbox_executes_reset_hook_when_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "PodFlow"',
                'entry_url: "https://example.com"',
                'description: "A podcast app"',
                "sandbox:",
                '  mode: "remote"',
                "  reset:",
                '    strategy: "hook"',
                '    url: "https://reset.example.com/hook"',
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
    spec = build_run_spec(product, skill)

    called: dict[str, object] = {}

    def fake_post(url: str, timeout: float) -> httpx.Response:
        called["url"] = url
        called["timeout"] = timeout
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr("doppel.sandbox.base.httpx.post", fake_post)

    sandbox = RemoteUrlSandbox(artifact_root=tmp_path / ".doppel" / "runs")
    ctx = sandbox.prepare(spec)
    reset_result = sandbox.reset(ctx)

    assert called["url"] == "https://reset.example.com/hook"
    assert called["timeout"] == 10.0
    assert reset_result.executed is True
    assert reset_result.strategy == "hook"
