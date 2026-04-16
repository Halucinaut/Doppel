from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doppel.config.models import RunSpec
from doppel.runtime.agent_runtime import RuntimeResult
from doppel.runtime.models import StepEvent
from doppel.sandbox.base import SandboxContext
from doppel.utils.paths import browser_use_env, resolve_playwright_executable


class BrowserUseUnavailableError(RuntimeError):
    """Raised when browser-use cannot be used in the current environment."""


@dataclass(slots=True)
class BrowserUseProvider:
    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None


def prepare_browser_use_environment(project_root: Path | None = None) -> dict[str, str]:
    env = browser_use_env(project_root)
    os.environ.update(env)
    os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")
    return env


def detect_browser_use_provider(spec: RunSpec | None = None) -> BrowserUseProvider:
    if spec is not None and spec.runtime_provider.provider != "auto":
        provider = spec.runtime_provider
        if provider.provider == "openai-compatible":
            return BrowserUseProvider(
                provider="openai-compatible",
                model=provider.runtime_model if provider.runtime_model != "unset" else "gpt-4o",
                api_key_env="DOPPEL_RUNTIME_API_KEY",
                base_url=str(provider.base_url) if provider.base_url else None,
            )
        if provider.provider == "openai":
            return BrowserUseProvider(provider="openai", model="gpt-4o", api_key_env="OPENAI_API_KEY")
        if provider.provider == "anthropic":
            return BrowserUseProvider(
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                api_key_env="ANTHROPIC_API_KEY",
            )
        if provider.provider == "google":
            return BrowserUseProvider(provider="google", model="gemini-2.5-flash", api_key_env="GOOGLE_API_KEY")

    custom_api_key = os.getenv("DOPPEL_RUNTIME_API_KEY")
    custom_base_url = os.getenv("DOPPEL_RUNTIME_BASE_URL")
    custom_model = os.getenv("DOPPEL_RUNTIME_MODEL")
    if custom_api_key:
        if not custom_base_url:
            raise BrowserUseUnavailableError(
                "DOPPEL_RUNTIME_BASE_URL is required when DOPPEL_RUNTIME_API_KEY is set."
            )
        return BrowserUseProvider(
            provider="openai-compatible",
            model=custom_model or "gpt-4o",
            api_key_env="DOPPEL_RUNTIME_API_KEY",
            base_url=custom_base_url,
        )
    if os.getenv("OPENAI_API_KEY"):
        return BrowserUseProvider(provider="openai", model="gpt-4o", api_key_env="OPENAI_API_KEY")
    if os.getenv("ANTHROPIC_API_KEY"):
        return BrowserUseProvider(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            api_key_env="ANTHROPIC_API_KEY",
        )
    if os.getenv("GOOGLE_API_KEY"):
        return BrowserUseProvider(provider="google", model="gemini-2.5-flash", api_key_env="GOOGLE_API_KEY")
    raise BrowserUseUnavailableError(
        "browser-use requires an LLM API key. Set DOPPEL_RUNTIME_API_KEY with DOPPEL_RUNTIME_BASE_URL "
        "for an OpenAI-compatible vision model, or set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY."
    )


def run_browser_use_agent(
    *,
    spec: RunSpec,
    ctx: SandboxContext,
    project_root: Path | None = None,
    show_browser: bool = False,
) -> RuntimeResult:
    project_root = project_root or Path.cwd()
    prepare_browser_use_environment(project_root)
    _apply_runtime_provider_env(spec)
    provider = detect_browser_use_provider(spec)
    llm = _build_llm(provider, spec)

    from browser_use import Agent, BrowserSession

    executable_path = resolve_playwright_executable(project_root)
    browser_session = BrowserSession(
        executable_path=str(executable_path) if executable_path else None,
        headless=not show_browser,
        user_data_dir=ctx.artifact_dir / "browser-profile",
        downloads_path=ctx.artifact_dir / "downloads",
        traces_dir=ctx.artifact_dir / "traces",
        window_size={"width": 1440, "height": 960},
    )

    task = _build_browser_use_task(spec, ctx)
    agent = Agent(
        task=task,
        llm=llm,
        browser_session=browser_session,
        use_vision=True,
        save_conversation_path=ctx.artifact_dir / "browser-use-conversation",
        use_judge=False,
        enable_planning=False,
        directly_open_url=True,
    )

    history = agent.run_sync(max_steps=spec.run_limits.max_steps)
    steps = _history_to_steps(history)
    stop_reason = _history_stop_reason(history)
    _close_browser_session(browser_session)
    return RuntimeResult(step_count=len(steps), stop_reason=stop_reason, steps=steps)


def _build_llm(provider: BrowserUseProvider, spec: RunSpec):
    requested_model = spec.llm_config.runtime_model
    model = requested_model if requested_model != "unset" else provider.model

    if provider.provider in {"openai", "openai-compatible"}:
        from browser_use.llm.openai.chat import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=os.getenv(provider.api_key_env),
            base_url=provider.base_url,
        )
    if provider.provider == "anthropic":
        from browser_use.llm.anthropic.chat import ChatAnthropic

        return ChatAnthropic(model=model, api_key=os.getenv(provider.api_key_env))
    if provider.provider == "google":
        from browser_use.llm.google.chat import ChatGoogle

        return ChatGoogle(model=model, api_key=os.getenv(provider.api_key_env))
    raise BrowserUseUnavailableError(f"Unsupported browser-use provider: {provider.provider}")


def _apply_runtime_provider_env(spec: RunSpec) -> None:
    provider = spec.runtime_provider
    if provider.provider == "openai-compatible":
        if provider.api_key:
            os.environ["DOPPEL_RUNTIME_API_KEY"] = provider.api_key
        if provider.base_url:
            os.environ["DOPPEL_RUNTIME_BASE_URL"] = str(provider.base_url)
        if provider.runtime_model != "unset":
            os.environ["DOPPEL_RUNTIME_MODEL"] = provider.runtime_model


def _build_browser_use_task(spec: RunSpec, ctx: SandboxContext) -> str:
    return (
        f"Entry URL: {ctx.entry_url}\n"
        f"Product: {spec.product.name}\n"
        f"Description: {spec.product.description}\n\n"
        f"Persona: {spec.persona.name}\n"
        f"Background: {spec.persona.background}\n"
        f"Goal: {spec.persona.goal}\n"
        f"Behavior style: {spec.persona.behavior_style}\n\n"
        f"Mission:\n{spec.skill.mission}\n\n"
        "Act from a first-time user's visual perspective. Prefer what is visible on the page over any hidden structure.\n"
        "Start from the provided Entry URL and treat it as the source of truth.\n"
        "Do not guess or invent alternate domains just from the product name.\n"
        "Only navigate away when the current page visibly offers a link or flow that a real user could follow.\n"
        "Only stop when the mission is complete, you would genuinely give up, or no further meaningful progress is possible."
    )


def _history_to_steps(history: Any) -> list[StepEvent]:
    steps: list[StepEvent] = []
    for index, item in enumerate(getattr(history, "history", []), start=1):
        action_type, action_input, target_description = _extract_action_details(item)
        error_message = _extract_error(item)
        status = "error" if error_message else ("stopped" if action_type == "stop" else "ok")
        timestamp = datetime.now(UTC).isoformat()
        duration_seconds = getattr(getattr(item, "metadata", None), "duration_seconds", 0.0) or 0.0
        reasoning_summary = _extract_reasoning(item)
        state = getattr(item, "state", None)
        steps.append(
            StepEvent(
                step_id=index,
                timestamp=timestamp,
                url=getattr(state, "url", ""),
                page_title=getattr(state, "title", None),
                action_type=action_type,
                action_input=action_input,
                target_description=target_description,
                observation_summary=f"Observed page {getattr(state, 'title', 'unknown')} at {getattr(state, 'url', '')}",
                reasoning_summary=reasoning_summary,
                screenshot_path=getattr(state, "screenshot_path", "") or "",
                elapsed_ms=int(duration_seconds * 1000),
                status=status,
                error_message=error_message,
            )
        )
    return steps


def _extract_action_details(item: Any) -> tuple[str, str | None, str | None]:
    model_output = getattr(item, "model_output", None)
    actions = getattr(model_output, "action", None) or []
    if not actions:
        return "wait", None, None

    dumped = actions[0].model_dump(exclude_none=True, mode="json")
    action_name = next(iter(dumped.keys()))
    params = dumped[action_name] or {}

    if "click" in action_name:
        return "click", None, f"{action_name}: {params}"
    if any(token in action_name for token in ["type", "input", "send", "fill"]):
        text = params.get("text") or params.get("value")
        return "input", text, f"{action_name}: {params}"
    if "scroll" in action_name:
        return "scroll", None, f"{action_name}: {params}"
    if action_name in {"done", "finish"}:
        return "stop", None, f"{action_name}: {params}"
    return "wait", None, f"{action_name}: {params}"


def _extract_reasoning(item: Any) -> str:
    model_output = getattr(item, "model_output", None)
    if not model_output:
        return "No reasoning captured."
    current_state = getattr(model_output, "current_state", None)
    if current_state:
        return (
            f"evaluation={getattr(current_state, 'evaluation_previous_goal', '')}; "
            f"next_goal={getattr(current_state, 'next_goal', '')}"
        )
    return "No reasoning captured."


def _extract_error(item: Any) -> str | None:
    results = getattr(item, "result", None) or []
    for result in results:
        error = getattr(result, "error", None)
        if error:
            return error
    return None


def _history_stop_reason(history: Any) -> str:
    if getattr(history, "is_done", lambda: False)():
        if getattr(history, "is_successful", lambda: False)():
            return "mission_completed"
        if getattr(history, "has_errors", lambda: False)():
            return "browser_use_error"
        return "agent_done_unsuccessful"
    if getattr(history, "has_errors", lambda: False)():
        return "browser_use_error"
    return "browser_use_finished"


def _close_browser_session(browser_session: Any) -> None:
    stop = getattr(browser_session, "stop", None)
    if stop is None:
        return
    if asyncio.iscoroutinefunction(stop):
        asyncio.run(stop())
    else:
        stop()
