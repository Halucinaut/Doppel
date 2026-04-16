from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from doppel.config.models import (
    PersonaConfig,
    PersonasFile,
    ProductConfig,
    RunSpec,
    RuntimeProviderConfig,
    SkillConfig,
)

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ConfigLoadError(ValueError):
    """Raised when a config file cannot be read or normalized."""


def load_yaml_file(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigLoadError(f"Failed to read config file: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigLoadError(f"Config file must contain a YAML object: {path}")

    return interpolate_env_vars(data)


def interpolate_env_vars(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: interpolate_env_vars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [interpolate_env_vars(item) for item in value]
    if isinstance(value, str):
        return ENV_VAR_PATTERN.sub(_replace_env_var, value)
    return value


def _replace_env_var(match: re.Match[str]) -> str:
    key = match.group(1)
    if key not in os.environ:
        raise ConfigLoadError(f"Missing environment variable: {key}")
    return os.environ[key]


def generate_default_persona(product: ProductConfig) -> PersonaConfig:
    return PersonaConfig(
        id="newcomer",
        name=f"First-time user for {product.name}",
        background="Arrived with no prior product knowledge.",
        goal="Understand the product and try its primary value.",
        behavior_style="Cautious, literal, leaves when confused.",
        tech_level="medium",
    )


def build_run_spec(
    product_path: Path,
    skill_path: Path,
    personas_path: Path | None = None,
    runtime_config_path: Path | None = None,
) -> RunSpec:
    product = ProductConfig.model_validate(load_yaml_file(product_path))
    skill = SkillConfig.model_validate(load_yaml_file(skill_path))
    runtime_provider = (
        RuntimeProviderConfig.model_validate(load_yaml_file(runtime_config_path))
        if runtime_config_path is not None
        else RuntimeProviderConfig()
    )

    if personas_path is None:
        persona = generate_default_persona(product)
    else:
        personas_file = PersonasFile.model_validate(load_yaml_file(personas_path))
        persona = resolve_persona(personas_file.personas, skill.persona)

    if personas_path is None and skill.persona != persona.id:
        skill = skill.model_copy(update={"persona": persona.id})

    llm_config_updates: dict[str, str] = {}
    if runtime_provider.runtime_model != "unset":
        llm_config_updates["runtime_model"] = runtime_provider.runtime_model
    if runtime_provider.judge_model != "unset":
        llm_config_updates["judge_model"] = runtime_provider.judge_model
    if runtime_provider.persona_model != "unset":
        llm_config_updates["persona_model"] = runtime_provider.persona_model

    return RunSpec(
        product=product,
        persona=persona,
        skill=skill,
        runtime_provider=runtime_provider,
        llm_config=llm_config_updates,
    )


def resolve_persona(personas: list[PersonaConfig], persona_id: str) -> PersonaConfig:
    for persona in personas:
        if persona.id == persona_id:
            return persona
    raise ConfigLoadError(f"Persona '{persona_id}' not found in personas file")
