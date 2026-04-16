from pathlib import Path

import typer
from pydantic import ValidationError

from doppel.config.loader import ConfigLoadError, build_run_spec


def validate(
    product: Path = typer.Option(..., "--product", exists=True, dir_okay=False, readable=True),
    skill: Path = typer.Option(..., "--skill", exists=True, dir_okay=False, readable=True),
    personas: Path | None = typer.Option(None, "--personas", exists=True, dir_okay=False, readable=True),
    runtime_config: Path | None = typer.Option(None, "--runtime-config", exists=True, dir_okay=False, readable=True),
) -> None:
    """Validate Doppel config files and print a summary."""
    try:
        spec = build_run_spec(
            product_path=product,
            skill_path=skill,
            personas_path=personas,
            runtime_config_path=runtime_config,
        )
    except (ConfigLoadError, ValidationError, ValueError) as exc:
        typer.echo(f"Config validation failed: {exc}")
        raise typer.Exit(code=1)

    typer.echo(
        "Config validation succeeded\n"
        f"- product: {spec.product.name}\n"
        f"- persona: {spec.persona.id}\n"
        f"- skill: {spec.skill.name}\n"
        f"- entry_url: {spec.product.entry_url}\n"
        f"- runtime_provider: {spec.runtime_provider.provider}"
    )
