from pathlib import Path

from typer.testing import CliRunner

from doppel.cli.main import app

runner = CliRunner()


def test_validate_command_succeeds_with_minimal_files(tmp_path: Path) -> None:
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

    result = runner.invoke(app, ["validate", "--product", str(product), "--skill", str(skill)])

    assert result.exit_code == 0
    assert "配置校验通过" in result.stdout
    assert "persona: newcomer" in result.stdout


def test_validate_command_fails_for_invalid_product(tmp_path: Path) -> None:
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "PodFlow"',
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

    result = runner.invoke(app, ["validate", "--product", str(product), "--skill", str(skill)])

    assert result.exit_code == 1
    assert "配置校验失败" in result.stdout


def test_validate_command_accepts_runtime_config(tmp_path: Path) -> None:
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
        ["validate", "--product", str(product), "--skill", str(skill), "--runtime-config", str(runtime)],
    )

    assert result.exit_code == 0
    assert "runtime_provider: openai-compatible" in result.stdout
