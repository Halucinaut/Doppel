from pathlib import Path

import typer

from doppel.runtime.batch import run_batch


def batch(
    product: Path = typer.Option(..., "--product", exists=True, dir_okay=False, readable=True),
    skill: list[Path] = typer.Option(
        [],
        "--skill",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Judge skill file. Repeat this option to run multiple personas.",
    ),
    skill_dir: Path | None = typer.Option(
        None,
        "--skill-dir",
        exists=True,
        file_okay=False,
        readable=True,
        help="Directory containing skill-*.yaml files.",
    ),
    personas: Path | None = typer.Option(None, "--personas", exists=True, dir_okay=False, readable=True),
    runtime_config: Path | None = typer.Option(None, "--runtime-config", exists=True, dir_okay=False, readable=True),
    artifact_root: Path | None = typer.Option(
        None,
        "--artifact-root",
        file_okay=False,
        dir_okay=True,
        writable=True,
        help="Override the output root directory. Defaults to <product_dir>/output.",
    ),
    real_browser: bool = typer.Option(False, "--real-browser", help="Use real Playwright browser for initial capture"),
    show_browser: bool = typer.Option(False, "--show-browser", help="Open a visible browser window"),
    decision_provider: str = typer.Option("capture-only", "--decision-provider"),
    retries: int = typer.Option(1, "--retries", min=0, help="Retry failed runs this many times."),
) -> None:
    """Run multiple Doppel skills and write a cross-persona summary."""
    skill_paths = list(skill)
    if skill_dir is not None:
        skill_paths.extend(sorted(skill_dir.glob("skill-*.yaml")))
    if not skill_paths:
        typer.echo("批量运行失败：必须提供至少一个 --skill 或 --skill-dir")
        raise typer.Exit(code=1)

    result = run_batch(
        product_path=product,
        skill_paths=skill_paths,
        personas_path=personas,
        runtime_config_path=runtime_config,
        artifact_root=artifact_root,
        use_real_browser=real_browser,
        decision_provider=decision_provider,
        show_browser=show_browser,
        retries=retries,
    )
    typer.echo(
        "批量运行已完成\n"
        f"- artifact_root: {result.artifact_root}\n"
        f"- run_count: {len(result.items)}\n"
        f"- summary: {result.summary_md_path}\n"
        f"- summary_json: {result.summary_json_path}"
    )
