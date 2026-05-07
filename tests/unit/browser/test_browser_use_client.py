import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from doppel.browser.browser_use_client import (
    BrowserUseUnavailableError,
    _build_browser_use_task,
    _enrich_click_evidence,
    _extract_json_object,
    detect_browser_use_provider,
    detect_browser_use_providers,
    run_browser_use_agent,
)
from doppel.config.loader import build_run_spec
from doppel.sandbox.remote import RemoteUrlSandbox


def _write_minimal_files(tmp_path: Path) -> tuple[Path, Path]:
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
    return product, skill


def test_detect_browser_use_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ["DOPPEL_RUNTIME_API_KEY", "DOPPEL_RUNTIME_BASE_URL", "DOPPEL_RUNTIME_MODEL"]:
        monkeypatch.delenv(key, raising=False)
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(BrowserUseUnavailableError):
        detect_browser_use_provider()


def test_detect_browser_use_provider_supports_openai_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOPPEL_RUNTIME_API_KEY", "test-key")
    monkeypatch.setenv("DOPPEL_RUNTIME_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("DOPPEL_RUNTIME_MODEL", "moonshotai/kimi-k2.5")
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    provider = detect_browser_use_provider()

    assert provider.provider == "openai-compatible"
    assert provider.model == "moonshotai/kimi-k2.5"
    assert provider.api_key_env == "DOPPEL_RUNTIME_API_KEY"
    assert provider.base_url == "https://integrate.api.nvidia.com/v1"


def test_detect_browser_use_provider_prefers_run_spec_runtime_config(tmp_path: Path) -> None:
    product, skill = _write_minimal_files(tmp_path)
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
    provider = detect_browser_use_provider(spec)

    assert provider.provider == "openai-compatible"
    assert provider.model == "moonshotai/kimi-k2.5"
    assert provider.base_url == "https://integrate.api.nvidia.com/v1"


def test_detect_browser_use_providers_includes_fallbacks(tmp_path: Path) -> None:
    product, skill = _write_minimal_files(tmp_path)
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
    providers = detect_browser_use_providers(spec)

    assert [provider.model for provider in providers] == ["glm-4.6v-flash", "moonshotai/kimi-k2.6"]
    assert [provider.api_key for provider in providers] == ["primary-key", "fallback-key"]


def test_run_browser_use_agent_parses_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    product, skill = _write_minimal_files(tmp_path)
    spec = build_run_spec(product, skill)
    ctx = RemoteUrlSandbox(artifact_root=tmp_path / ".doppel" / "runs").prepare(spec)

    class FakeAction:
        def model_dump(self, exclude_none=True, mode="json"):
            return {"click_element": {"index": 1}}

    fake_history_item = SimpleNamespace(
        model_output=SimpleNamespace(
            action=[FakeAction()],
            current_state=SimpleNamespace(
                evaluation_previous_goal="Found the CTA",
                next_goal="Click the CTA",
            ),
        ),
        state=SimpleNamespace(
            url="https://example.com",
            title="Home",
            screenshot_path=str(ctx.artifact_dir / "screenshots" / "step-001.png"),
        ),
        metadata=SimpleNamespace(duration_seconds=0.2),
        result=[SimpleNamespace(error=None, is_done=True, success=True)],
    )
    fake_history = SimpleNamespace(
        history=[fake_history_item],
        has_errors=lambda: False,
        is_done=lambda: True,
        is_successful=lambda: True,
    )

    class FakeBrowserSession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def stop(self):
            return None

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_sync(self, max_steps: int):
            assert max_steps == spec.run_limits.max_steps
            return fake_history

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("doppel.browser.browser_use_client.resolve_playwright_executable", lambda project_root: None)
    monkeypatch.setitem(os.environ, "BROWSER_USE_CONFIG_DIR", str(tmp_path / ".browseruse"))
    monkeypatch.setattr("browser_use.Agent", FakeAgent, raising=True)
    monkeypatch.setattr("browser_use.BrowserSession", FakeBrowserSession, raising=True)
    monkeypatch.setattr("browser_use.llm.openai.chat.ChatOpenAI", FakeChatOpenAI, raising=True)

    result = run_browser_use_agent(spec=spec, ctx=ctx, project_root=tmp_path)

    assert result.step_count == 1
    assert result.stop_reason == "mission_completed"
    assert result.steps[0].action_type == "click"


def test_run_browser_use_agent_uses_openai_compatible_base_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DOPPEL_RUNTIME_API_KEY", "custom-key")
    monkeypatch.setenv("DOPPEL_RUNTIME_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("DOPPEL_RUNTIME_MODEL", "moonshotai/kimi-k2.5")

    product, skill = _write_minimal_files(tmp_path)
    spec = build_run_spec(product, skill)
    ctx = RemoteUrlSandbox(artifact_root=tmp_path / ".doppel" / "runs").prepare(spec)

    class FakeAction:
        def model_dump(self, exclude_none=True, mode="json"):
            return {"done": {}}

    fake_history_item = SimpleNamespace(
        model_output=SimpleNamespace(
            action=[FakeAction()],
            current_state=SimpleNamespace(
                evaluation_previous_goal="Task complete",
                next_goal="Stop",
            ),
        ),
        state=SimpleNamespace(
            url="https://example.com",
            title="Home",
            screenshot_path=str(ctx.artifact_dir / "screenshots" / "step-001.png"),
        ),
        metadata=SimpleNamespace(duration_seconds=0.1),
        result=[SimpleNamespace(error=None, is_done=True, success=True)],
    )
    fake_history = SimpleNamespace(
        history=[fake_history_item],
        has_errors=lambda: False,
        is_done=lambda: True,
        is_successful=lambda: True,
    )
    captured_llm_kwargs: dict[str, object] = {}

    class FakeBrowserSession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def stop(self):
            return None

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_sync(self, max_steps: int):
            assert max_steps == spec.run_limits.max_steps
            return fake_history

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured_llm_kwargs.update(kwargs)

    monkeypatch.setattr("doppel.browser.browser_use_client.resolve_playwright_executable", lambda project_root: None)
    monkeypatch.setitem(os.environ, "BROWSER_USE_CONFIG_DIR", str(tmp_path / ".browseruse"))
    monkeypatch.setattr("browser_use.Agent", FakeAgent, raising=True)
    monkeypatch.setattr("browser_use.BrowserSession", FakeBrowserSession, raising=True)
    monkeypatch.setattr("browser_use.llm.openai.chat.ChatOpenAI", FakeChatOpenAI, raising=True)

    result = run_browser_use_agent(spec=spec, ctx=ctx, project_root=tmp_path)

    assert result.stop_reason == "mission_completed"
    assert captured_llm_kwargs["model"] == "moonshotai/kimi-k2.5"
    assert captured_llm_kwargs["api_key"] == "custom-key"
    assert captured_llm_kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"


def test_history_stop_reason_prefers_success_over_transient_errors() -> None:
    from doppel.browser.browser_use_client import _history_stop_reason

    fake_history = SimpleNamespace(
        has_errors=lambda: True,
        is_done=lambda: True,
        is_successful=lambda: True,
    )

    assert _history_stop_reason(fake_history) == "mission_completed"


def test_extract_json_object_sanitizes_control_characters() -> None:
    payload = _extract_json_object(
        '{"evaluation_previous_goal":"页面加载\u0007完成","memory":"已看到内容","next_goal":"结束","action":[{"done":{"text":"完成","success":true}}]}'
    )

    assert payload["evaluation_previous_goal"] == "页面加载完成"


def test_build_browser_use_task_requires_scroll_when_criterion_exists(tmp_path: Path) -> None:
    product, skill = _write_minimal_files(tmp_path)
    skill.write_text(
        skill.read_text(encoding="utf-8")
        + "\n"
        + "\n".join(
            [
                '  - id: "scroll_discovery"',
                '    question: "下滑后是否有信息递进？"',
                '    good: "有递进"',
                '    bad: "无递进"',
            ]
        ),
        encoding="utf-8",
    )
    spec = build_run_spec(product, skill)
    ctx = RemoteUrlSandbox(artifact_root=tmp_path / ".doppel" / "runs").prepare(spec)

    task = _build_browser_use_task(spec, ctx)

    assert "必须至少执行一次向下 scroll" in task


def test_enrich_click_evidence_uses_interacted_element_label_and_bounds(tmp_path: Path) -> None:
    from PIL import Image

    screenshot_path = tmp_path / "step-001.png"
    Image.new("RGB", (1440, 960), "white").save(screenshot_path)
    node = SimpleNamespace(
        attributes={"placeholder": "站内AI工具搜索"},
        bounds=SimpleNamespace(x=100, y=120, width=240, height=48),
    )
    item = SimpleNamespace(state=SimpleNamespace(interacted_element=[node]))

    label, annotated_path = _enrich_click_evidence(
        item=item,
        target_description="click: {'index': 70}",
        screenshot_path=str(screenshot_path),
    )

    assert label == "站内AI工具搜索"
    assert annotated_path.endswith("-click.png")
    assert Path(annotated_path).exists()
