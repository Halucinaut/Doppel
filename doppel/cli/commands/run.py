from pathlib import Path

import typer

from doppel.runtime.orchestrator import run_pipeline


def run(
    product: Path = typer.Option(..., "--product", exists=True, dir_okay=False, readable=True),
    skill: Path = typer.Option(..., "--skill", exists=True, dir_okay=False, readable=True),
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
    show_browser: bool = typer.Option(
        False,
        "--show-browser",
        help="Open a visible browser window so you can watch the agent actions live.",
    ),
    decision_provider: str = typer.Option(
        "capture-only",
        "--decision-provider",
        help=(
            "Decision provider: capture-only or browser-use. "
            "For custom OpenAI-compatible vision backends, set DOPPEL_RUNTIME_API_KEY, "
            "DOPPEL_RUNTIME_BASE_URL, and optionally DOPPEL_RUNTIME_MODEL."
        ),
    ),
) -> None:
    """Run the current scaffolded pipeline and write initial artifacts."""
    result = run_pipeline(
        product_path=product,
        skill_path=skill,
        personas_path=personas,
        runtime_config_path=runtime_config,
        artifact_root=artifact_root,
        use_real_browser=real_browser,
        decision_provider=decision_provider,
        show_browser=show_browser,
    )
    typer.echo(
        "Run scaffold completed\n"
        f"- run_id: {result.run_id}\n"
        f"- mode: {result.mode}\n"
        f"- artifact_dir: {result.artifact_dir}\n"
        f"- step_count: {result.step_count}\n"
        f"- stop_reason: {result.stop_reason}\n"
        f"- report: {result.report_path}"
    )
    if result.error_message:
        typer.echo(f"Runtime error: {result.error_message}")
        raise typer.Exit(code=1)
