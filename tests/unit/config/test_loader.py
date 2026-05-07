from pathlib import Path

import pytest

from doppel.config.loader import ConfigLoadError, build_run_spec


def test_build_run_spec_with_explicit_persona(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_PASSWORD", "secret-123")
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "PodFlow"',
                'entry_url: "https://example.com"',
                'description: "A podcast app"',
                "auth:",
                "  required: true",
                '  username: "test@example.com"',
                '  password: "${TEST_PASSWORD}"',
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
    personas = tmp_path / "personas.yaml"
    personas.write_text(
        "\n".join(
            [
                "personas:",
                '  - id: "newcomer"',
                '    name: "Alex"',
                '    background: "New here"',
                '    goal: "Try the product"',
                '    behavior_style: "Careful"',
                '    tech_level: "low"',
            ]
        ),
        encoding="utf-8",
    )

    spec = build_run_spec(product, skill, personas)

    assert spec.product.auth.password == "secret-123"
    assert spec.persona.id == "newcomer"
    assert spec.skill.persona == "newcomer"


def test_build_run_spec_generates_default_persona_when_missing(tmp_path: Path) -> None:
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
                'persona: "ignored-for-default"',
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

    assert spec.persona.id == "newcomer"
    assert spec.skill.persona == "newcomer"


def test_build_run_spec_raises_for_missing_env_var(tmp_path: Path) -> None:
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "PodFlow"',
                'entry_url: "https://example.com"',
                'description: "A podcast app"',
                "auth:",
                "  required: true",
                '  username: "test@example.com"',
                '  password: "${MISSING_PASSWORD}"',
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

    with pytest.raises(ConfigLoadError, match="Missing environment variable"):
        build_run_spec(product, skill)


def test_build_run_spec_requires_reset_hook_url(tmp_path: Path) -> None:
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "PodFlow"',
                'entry_url: "https://example.com"',
                'description: "A podcast app"',
                "sandbox:",
                "  reset:",
                '    strategy: "hook"',
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

    with pytest.raises(ValueError, match="sandbox.reset.url is required"):
        build_run_spec(product, skill)


def test_build_run_spec_loads_runtime_provider_config(tmp_path: Path) -> None:
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

    spec = build_run_spec(product, skill, runtime_config_path=runtime)

    assert spec.runtime_provider.provider == "openai-compatible"
    assert spec.runtime_provider.api_key == "test-key"
    assert str(spec.runtime_provider.base_url) == "https://integrate.api.nvidia.com/v1"
    assert spec.llm_config.runtime_model == "moonshotai/kimi-k2.5"


def test_build_run_spec_loads_runtime_provider_fallbacks(tmp_path: Path) -> None:
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
                'api_key: "primary-key"',
                'base_url: "https://open.bigmodel.cn/api/paas/v4"',
                'runtime_model: "glm-4.6v-flash"',
                "fallback_providers:",
                '  - provider: "openai-compatible"',
                '    api_key: "fallback-key"',
                '    base_url: "https://integrate.api.nvidia.com/v1"',
                '    runtime_model: "moonshotai/kimi-k2.6"',
            ]
        ),
        encoding="utf-8",
    )

    spec = build_run_spec(product, skill, runtime_config_path=runtime)

    assert len(spec.runtime_provider.fallback_providers) == 1
    assert spec.runtime_provider.fallback_providers[0].runtime_model == "moonshotai/kimi-k2.6"
