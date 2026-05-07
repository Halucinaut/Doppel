from pathlib import Path

from typer.testing import CliRunner

from doppel.cli.main import app

runner = CliRunner()


def test_cli_run_smoke_writes_core_artifacts(tmp_path: Path) -> None:
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

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["run", "--product", str(product), "--skill", str(skill)])

        assert result.exit_code == 0
        assert "运行主链路已完成" in result.stdout
        runs_dir = tmp_path / "output"
        run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]
        assert (run_dir / "session.json").exists()
        assert (run_dir / "facts.json").exists()
        assert (run_dir / "evaluation.json").exists()
        assert (run_dir / "report.md").exists()
