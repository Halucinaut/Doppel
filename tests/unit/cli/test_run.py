from pathlib import Path

from typer.testing import CliRunner

from doppel.cli.main import app

runner = CliRunner()


def test_run_command_succeeds_in_capture_only_mode(tmp_path: Path) -> None:
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

    result = runner.invoke(app, ["run", "--product", str(product), "--skill", str(skill)])

    assert result.exit_code == 0
    assert "stop_reason: capture_only" in result.stdout
    assert str(tmp_path / "output") in result.stdout


def test_run_command_fails_when_browser_use_requested_without_api_key(tmp_path: Path, monkeypatch) -> None:
    for key in ["DOPPEL_RUNTIME_API_KEY", "DOPPEL_RUNTIME_BASE_URL", "DOPPEL_RUNTIME_MODEL"]:
        monkeypatch.delenv(key, raising=False)
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)

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

    result = runner.invoke(
        app,
        [
            "run",
            "--decision-provider",
            "browser-use",
            "--product",
            str(product),
            "--skill",
            str(skill),
        ],
    )

    assert result.exit_code == 1
    assert "运行时错误：browser-use requires an LLM API key" in result.stdout
    assert "DOPPEL_RUNTIME_API_KEY" in result.stdout


def test_run_command_accepts_runtime_config(tmp_path: Path) -> None:
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
    runtime = tmp_path / "runtime.yaml"
    runtime.write_text(
        "\n".join(
            [
                'provider: "openai-compatible"',
                'api_key: "test-key"',
                'base_url: "https://integrate.api.nvidia.com/v1"',
                'runtime_model: "moonshotai/kimi-k2.5"',
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["run", "--product", str(product), "--skill", str(skill), "--runtime-config", str(runtime)],
    )

    assert result.exit_code == 0
    assert "stop_reason: capture_only" in result.stdout


def test_run_command_accepts_artifact_root_override(tmp_path: Path) -> None:
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
    output_dir = tmp_path / "custom-output"

    result = runner.invoke(
        app,
        [
            "run",
            "--product",
            str(product),
            "--skill",
            str(skill),
            "--artifact-root",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert str(output_dir) in result.stdout
