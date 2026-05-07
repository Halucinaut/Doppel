from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doppel.config.models import RunSpec, RuntimeProviderEndpoint
from doppel.runtime.agent_runtime import RuntimeResult
from doppel.runtime.models import StepEvent
from doppel.sandbox.base import SandboxContext
from doppel.utils.paths import browser_use_env, resolve_playwright_executable


class RetryableChatOpenAI:
    """给 OpenAI 兼容模型补上异步重试与宽松结构化输出解析。"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, **kwargs: Any):
        from browser_use.llm.openai.chat import ChatOpenAI

        self.model = kwargs.get("model", "")
        self.name = self.model
        self.provider = "openai-compatible"
        self._llm = ChatOpenAI(**kwargs)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def __call__(self, *args: Any, **kwargs: Any):
        return await self.ainvoke(*args, **kwargs)

    async def ainvoke(self, messages: list[Any], output_format: type[Any] | None = None, **kwargs: Any):
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                if output_format is None:
                    return await self._llm.ainvoke(messages, output_format=output_format, **kwargs)
                return await self._ainvoke_structured(messages, output_format, **kwargs)
            except Exception as e:
                last_exception = e
                if _is_retryable_llm_error(e) and attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
        raise last_exception

    async def _ainvoke_structured(self, messages: list[Any], output_format: type[Any], **kwargs: Any):
        from browser_use.llm.openai.chat import OpenAIMessageSerializer
        from browser_use.llm.views import ChatInvokeCompletion

        openai_messages = OpenAIMessageSerializer.serialize_messages(messages)
        schema = output_format.model_json_schema()
        _append_structured_output_instruction(openai_messages, schema)

        response = await self._llm.get_client().chat.completions.create(
            model=self._llm.model,
            messages=openai_messages,
            **_openai_model_params(self._llm),
        )
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.message.content is None:
            raise RuntimeError("模型返回为空，无法解析 browser-use 动作")

        payload = _extract_json_object(choice.message.content)
        parsed = output_format.model_validate(_normalize_agent_output(payload))
        return ChatInvokeCompletion(
            completion=parsed,
            usage=self._llm._get_usage(response),
            stop_reason=choice.finish_reason,
        )

    def __getattr__(self, name):
        return getattr(self._llm, name)


class RotatingChatModel:
    """按顺序轮转多个模型，避免单个供应商短时不可用拖垮整轮测试。"""

    def __init__(self, llms: list[Any]):
        if not llms:
            raise BrowserUseUnavailableError("No browser-use LLM provider is available.")
        self._llms = llms
        self._index = 0
        self.model = " -> ".join(getattr(llm, "model", "unknown") for llm in llms)
        self.name = self.model
        self.provider = "rotating"

    async def __call__(self, *args: Any, **kwargs: Any):
        return await self.ainvoke(*args, **kwargs)

    async def ainvoke(self, messages: list[Any], output_format: type[Any] | None = None, **kwargs: Any):
        last_exception = None
        for index in range(self._index, len(self._llms)):
            llm = self._llms[index]
            try:
                result = await llm.ainvoke(messages, output_format=output_format, **kwargs)
                self._index = index
                return result
            except Exception as exc:
                last_exception = exc
                if index < len(self._llms) - 1 and _is_retryable_llm_error(exc):
                    self._index = index + 1
                    continue
                raise
        raise last_exception

    def __getattr__(self, name: str):
        return getattr(self._llms[self._index], name)


class BrowserUseUnavailableError(RuntimeError):
    """Raised when browser-use cannot be used in the current environment."""


@dataclass(slots=True)
class BrowserUseProvider:
    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None
    api_key: str | None = None


def prepare_browser_use_environment(project_root: Path | None = None) -> dict[str, str]:
    env = browser_use_env(project_root)
    os.environ.update(env)
    os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")
    return env


def detect_browser_use_provider(spec: RunSpec | None = None) -> BrowserUseProvider:
    return detect_browser_use_providers(spec)[0]


def detect_browser_use_providers(spec: RunSpec | None = None) -> list[BrowserUseProvider]:
    if spec is not None and spec.runtime_provider.provider != "auto":
        runtime_provider = spec.runtime_provider
        providers = [_runtime_endpoint_to_browser_provider(runtime_provider)]
        providers.extend(_runtime_endpoint_to_browser_provider(provider) for provider in runtime_provider.fallback_providers)
        return providers

    custom_api_key = os.getenv("DOPPEL_RUNTIME_API_KEY")
    custom_base_url = os.getenv("DOPPEL_RUNTIME_BASE_URL")
    custom_model = os.getenv("DOPPEL_RUNTIME_MODEL")
    if custom_api_key:
        if not custom_base_url:
            raise BrowserUseUnavailableError(
                "DOPPEL_RUNTIME_BASE_URL is required when DOPPEL_RUNTIME_API_KEY is set."
            )
        return [
            BrowserUseProvider(
                provider="openai-compatible",
                model=custom_model or "gpt-4o",
                api_key_env="DOPPEL_RUNTIME_API_KEY",
                base_url=custom_base_url,
            )
        ]
    if os.getenv("OPENAI_API_KEY"):
        return [BrowserUseProvider(provider="openai", model="gpt-4o", api_key_env="OPENAI_API_KEY")]
    if os.getenv("ANTHROPIC_API_KEY"):
        return [
            BrowserUseProvider(
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                api_key_env="ANTHROPIC_API_KEY",
            )
        ]
    if os.getenv("GOOGLE_API_KEY"):
        return [BrowserUseProvider(provider="google", model="gemini-2.5-flash", api_key_env="GOOGLE_API_KEY")]
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
    providers = detect_browser_use_providers(spec)
    llm = _build_llm(providers, spec)

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
        use_thinking=False,
        max_actions_per_step=1,
        llm_timeout=60,
        max_clickable_elements_length=6000,
        vision_detail_level="low",
        directly_open_url=False,
        initial_actions=[{"navigate": {"url": ctx.entry_url, "new_tab": False}}],
    )

    history = agent.run_sync(max_steps=spec.run_limits.max_steps)
    steps = _history_to_steps(history)
    stop_reason = _history_stop_reason(history)
    _close_browser_session(browser_session)
    return RuntimeResult(step_count=len(steps), stop_reason=stop_reason, steps=steps)


def _build_llm(providers: BrowserUseProvider | list[BrowserUseProvider], spec: RunSpec):
    provider_list = providers if isinstance(providers, list) else [providers]
    llms = [_build_single_llm(provider) for provider in provider_list]
    return llms[0] if len(llms) == 1 else RotatingChatModel(llms)


def _build_single_llm(provider: BrowserUseProvider):
    api_key = provider.api_key or os.getenv(provider.api_key_env)
    if provider.provider in {"openai", "openai-compatible"}:
        return RetryableChatOpenAI(
            model=provider.model,
            api_key=api_key,
            base_url=provider.base_url,
            max_retries=3,
            retry_delay=1.0,
            add_schema_to_system_prompt=True,
            dont_force_structured_output=True,
            timeout=60.0,
        )
    if provider.provider == "anthropic":
        from browser_use.llm.anthropic.chat import ChatAnthropic

        return ChatAnthropic(model=provider.model, api_key=api_key)
    if provider.provider == "google":
        from browser_use.llm.google.chat import ChatGoogle

        return ChatGoogle(model=provider.model, api_key=api_key)
    raise BrowserUseUnavailableError(f"Unsupported browser-use provider: {provider.provider}")


def _runtime_endpoint_to_browser_provider(endpoint: RuntimeProviderEndpoint) -> BrowserUseProvider:
    if endpoint.provider == "openai-compatible":
        return BrowserUseProvider(
            provider="openai-compatible",
            model=endpoint.runtime_model if endpoint.runtime_model != "unset" else "gpt-4o",
            api_key_env="DOPPEL_RUNTIME_API_KEY",
            base_url=str(endpoint.base_url) if endpoint.base_url else None,
            api_key=endpoint.api_key,
        )
    if endpoint.provider == "openai":
        return BrowserUseProvider(
            provider="openai",
            model=endpoint.runtime_model if endpoint.runtime_model != "unset" else "gpt-4o",
            api_key_env="OPENAI_API_KEY",
            api_key=endpoint.api_key,
        )
    if endpoint.provider == "anthropic":
        return BrowserUseProvider(
            provider="anthropic",
            model=endpoint.runtime_model if endpoint.runtime_model != "unset" else "claude-3-5-sonnet-latest",
            api_key_env="ANTHROPIC_API_KEY",
            api_key=endpoint.api_key,
        )
    if endpoint.provider == "google":
        return BrowserUseProvider(
            provider="google",
            model=endpoint.runtime_model if endpoint.runtime_model != "unset" else "gemini-2.5-flash",
            api_key_env="GOOGLE_API_KEY",
            api_key=endpoint.api_key,
        )
    raise BrowserUseUnavailableError(f"Unsupported browser-use provider: {endpoint.provider}")


def _append_structured_output_instruction(openai_messages: list[dict[str, Any]], schema: dict[str, Any]) -> None:
    instruction = (
        "\n<强制输出协议>\n"
        "你必须只返回一个 JSON 对象。禁止返回 Markdown、代码块、解释文字、前后缀、注释或多个 JSON。\n"
        "JSON 根对象必须包含这些字段：evaluation_previous_goal、memory、next_goal、action。\n"
        "action 必须是非空数组，且每次只能包含 1 个动作对象。\n"
        "允许的动作只有 wait、scroll、click、done。禁止 search、navigate、go_back、extract、evaluate、read_file、write_file。\n"
        "如果需要等待，返回：{\"evaluation_previous_goal\":\"页面仍在加载\",\"memory\":\"继续等待页面内容\",\"next_goal\":\"等待页面显示内容\",\"action\":[{\"wait\":{}}]}\n"
        "如果需要向下滚动，返回：{\"evaluation_previous_goal\":\"首屏信息不足\",\"memory\":\"需要查看更多内容\",\"next_goal\":\"向下滚动一次\",\"action\":[{\"scroll\":{\"down\":true,\"pages\":1}}]}\n"
        "如果需要点击元素，必须使用当前 browser_state 中存在的元素 index，返回：{\"evaluation_previous_goal\":\"发现主入口\",\"memory\":\"准备验证入口\",\"next_goal\":\"点击主入口\",\"action\":[{\"click\":{\"index\":数字}}]}\n"
        "如果已经能总结，返回：{\"evaluation_previous_goal\":\"已获得足够信息\",\"memory\":\"任务完成\",\"next_goal\":\"结束任务\",\"action\":[{\"done\":{\"text\":\"中文总结\",\"success\":true}}]}\n"
        "JSON 对象里的所有字符串字段必须使用中文。\n"
        "</强制输出协议>\n"
        "JSON Schema 仅用于补充字段约束：\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )
    if not openai_messages:
        openai_messages.append({"role": "system", "content": instruction})
        return
    first = openai_messages[0]
    content = first.get("content")
    if isinstance(content, str):
        first["content"] = content + instruction
    elif isinstance(content, list):
        content.append({"type": "text", "text": instruction})
    else:
        first["content"] = instruction


def _openai_model_params(llm: Any) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for key in ["temperature", "frequency_penalty", "max_completion_tokens", "top_p", "seed", "service_tier"]:
        value = getattr(llm, key, None)
        if value is not None:
            params[key] = value
    return params


def _extract_json_object(content: str) -> dict[str, Any]:
    text = _sanitize_json_text(content).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start < 0:
        raise ValueError(f"模型未返回 JSON 对象：{content[:200]}")
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                parsed = json.loads(text[start : index + 1])
                if not isinstance(parsed, dict):
                    raise ValueError("模型 JSON 根节点不是对象")
                return parsed
    raise ValueError(f"模型 JSON 对象未闭合：{content[:200]}")


def _sanitize_json_text(content: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", content)


def _normalize_agent_output(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("evaluation_previous_goal", "未提供上一步评估。")
    normalized.setdefault("memory", "未提供记忆。")
    normalized.setdefault("next_goal", "继续完成任务。")
    if "action" not in normalized or not isinstance(normalized["action"], list) or not normalized["action"]:
        normalized["action"] = [_fallback_action_from_payload(normalized)]

    actions: list[Any] = []
    for action in normalized["action"][:1]:
        actions.append(_normalize_action(action) if isinstance(action, dict) else action)
    if not actions or not isinstance(actions[0], dict) or not actions[0]:
        actions = [_fallback_action_from_payload(normalized)]
    normalized["action"] = actions
    return normalized


def _normalize_action(action: dict[str, Any]) -> dict[str, Any]:
    if not action:
        return {"wait": {}}
    if "wait" in action and isinstance(action["wait"], dict):
        return {"wait": {}}
    if "scroll" in action:
        scroll = action["scroll"] if isinstance(action["scroll"], dict) else {}
        return {"scroll": {"down": bool(scroll.get("down", True)), "pages": float(scroll.get("pages", 1.0))}}
    if "click" in action:
        click = action["click"] if isinstance(action["click"], dict) else {}
        index = click.get("index") or click.get("element_index")
        if isinstance(index, str) and index.isdigit():
            index = int(index)
        if isinstance(index, int):
            return {"click": {"index": index}}
        return {"wait": {}}
    if "done" in action and isinstance(action["done"], str):
        return {"done": {"text": action["done"], "success": True}}
    if "done" in action and isinstance(action["done"], dict):
        done = dict(action["done"])
        done.setdefault("success", True)
        if "text" not in done:
            done["text"] = done.get("summary") or done.get("message") or "任务已完成。"
        return {"done": done}
    return action


def _fallback_action_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False)
    done_tokens = ["完成", "总结", "足够信息", "结束任务", "可以结束", "任务完成"]
    if any(token in text for token in done_tokens):
        summary = payload.get("memory") or payload.get("next_goal") or "已获得足够信息，结束任务。"
        return {"done": {"text": str(summary), "success": True}}
    return {"wait": {}}


def _is_retryable_llm_error(error: Exception) -> bool:
    message = str(error).lower()
    retryable_tokens = [
        "访问量过大",
        "rate limit",
        "too many requests",
        "429",
        "1305",
        "timeout",
        "timed out",
        "connection",
        "temporarily",
        "service unavailable",
        "503",
        "502",
        "410",
        "404",
        "json",
        "parse",
        "validation",
        "structured output",
        "failed to output in the right format",
    ]
    return any(token in message for token in retryable_tokens)


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
    criteria_ids = [criterion.id for criterion in spec.skill.judge_criteria]
    requires_scroll_discovery = any("scroll" in criterion_id.lower() for criterion_id in criteria_ids)
    scroll_instruction = (
        "本次评判包含滚动发现：首屏出现有效内容后，必须至少执行一次向下 scroll，再决定是否 done；"
        "只有页面明确不可滚动或滚动会离开真实用户路径时，才可以说明原因并 done。\n"
        if requires_scroll_discovery
        else "如果已经获得足够信息，必须立即 done，不要继续滚动或等待。\n"
    )
    return (
        f"入口 URL：{ctx.entry_url}\n"
        f"产品名称：{spec.product.name}\n"
        f"产品描述：{spec.product.description}\n\n"
        f"用户画像：{spec.persona.name}\n"
        f"背景：{spec.persona.background}\n"
        f"目标：{spec.persona.goal}\n"
        f"行为风格：{spec.persona.behavior_style}\n\n"
        f"任务：\n{spec.skill.mission}\n\n"
        f"评判标准 ID：{', '.join(criteria_ids)}\n\n"
        "请以第一次进入该产品的真实用户视角行动，优先依据页面上可见的视觉信息，不要依赖隐藏结构。\n"
        "必须从给定入口 URL 开始，并把它视为唯一可信入口。\n"
        "如果当前标签页是 about:blank，必须先导航到入口 URL，不要在空白页反复等待。\n"
        "不要只根据产品名称猜测或编造其他域名。\n"
        "禁止使用搜索引擎、替代网站、第三方评测页面或任何入口 URL 之外的资料。\n"
        "如果入口 URL 无法加载或长期空白，只能刷新、等待、在当前页面滚动，或基于当前页面可见状态结束任务。\n"
        "只有当当前页面清楚提供了真实用户可以跟随的链接或流程时，才可以离开当前页面。\n"
        "动作协议必须严格遵守：每一步只能返回一个动作；只允许 wait、scroll、click、done；禁止 search、navigate、extract、evaluate。\n"
        f"{scroll_instruction}"
        "所有观察、推理、计划、动作说明和完成总结必须使用中文。\n"
        "done.text 必须用中文总结产品定位、核心价值、主要入口、浏览路径和放弃或继续使用的理由。\n"
        "只有在任务完成、你会真实放弃、或已经没有有意义的下一步时才停止。"
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
        screenshot_path = getattr(state, "screenshot_path", "") or ""
        if action_type == "click":
            target_description, screenshot_path = _enrich_click_evidence(
                item=item,
                target_description=target_description,
                screenshot_path=screenshot_path,
            )
        steps.append(
            StepEvent(
                step_id=index,
                timestamp=timestamp,
                url=getattr(state, "url", ""),
                page_title=getattr(state, "title", None),
                action_type=action_type,
                action_input=action_input,
                target_description=target_description,
                observation_summary=f"观察到页面「{getattr(state, 'title', '未知')}」，URL：{getattr(state, 'url', '')}",
                reasoning_summary=reasoning_summary,
                screenshot_path=screenshot_path,
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


def _enrich_click_evidence(*, item: Any, target_description: str | None, screenshot_path: str) -> tuple[str | None, str]:
    click_index = _click_index_from_target(target_description)
    if click_index is None:
        return target_description, screenshot_path

    node = _selector_node(item, click_index)
    label = _node_label(node)
    if label:
        target_description = label

    rect = _node_rect(node)
    annotated_path = _annotate_click_screenshot(screenshot_path=screenshot_path, rect=rect, index=click_index)
    return target_description, annotated_path or screenshot_path


def _click_index_from_target(target_description: str | None) -> int | None:
    if not target_description:
        return None
    match = re.search(r"'index':\s*(\d+)|\"index\":\s*(\d+)|index=(\d+)", target_description)
    if not match:
        return None
    value = next(group for group in match.groups() if group)
    return int(value)


def _selector_node(item: Any, index: int) -> Any | None:
    state = getattr(item, "state", None)
    interacted_elements = getattr(state, "interacted_element", None) or []
    for element in interacted_elements:
        if element is not None:
            return element
    dom_state = getattr(state, "dom_state", None)
    selector_map = getattr(dom_state, "selector_map", None) or {}
    return selector_map.get(index)


def _node_label(node: Any | None) -> str | None:
    if node is None:
        return None
    ax_node = getattr(node, "ax_node", None)
    ax_name = getattr(ax_node, "name", None) or getattr(node, "ax_name", None)
    attributes = getattr(node, "attributes", None) or {}
    node_value = getattr(node, "node_value", None)
    label = (
        ax_name
        or attributes.get("aria-label")
        or attributes.get("title")
        or attributes.get("placeholder")
        or attributes.get("alt")
        or getattr(node, "text", None)
        or getattr(node, "inner_text", None)
        or getattr(node, "all_text_till_next_clickable_element", None)
        or node_value
    )
    if isinstance(label, dict):
        label = label.get("value")
    if not label:
        return None
    normalized = re.sub(r"\s+", " ", str(label)).strip()
    return normalized[:80] if normalized else None


def _node_rect(node: Any | None) -> tuple[float, float, float, float] | None:
    rect = getattr(node, "absolute_position", None) if node is not None else None
    if rect is None:
        rect = getattr(node, "bounds", None) if node is not None else None
    if rect is None:
        rect = getattr(node, "viewport_coordinates", None) if node is not None else None
    if isinstance(rect, dict):
        width = float(rect.get("width") or rect.get("w") or 0)
        height = float(rect.get("height") or rect.get("h") or 0)
        if width <= 0 or height <= 0:
            return None
        return (
            float(rect.get("x") or rect.get("left") or 0),
            float(rect.get("y") or rect.get("top") or 0),
            width,
            height,
        )
    if rect is None:
        return None
    width = float(getattr(rect, "width", 0) or 0)
    height = float(getattr(rect, "height", 0) or 0)
    if width <= 0 or height <= 0:
        return None
    return (
        float(getattr(rect, "x", 0) or 0),
        float(getattr(rect, "y", 0) or 0),
        width,
        height,
    )


def _annotate_click_screenshot(
    *, screenshot_path: str, rect: tuple[float, float, float, float] | None, index: int
) -> str | None:
    if not screenshot_path or rect is None:
        return None
    path = Path(screenshot_path)
    if not path.exists():
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    x, y, width, height = rect
    annotated_path = path.with_name(f"{path.stem}-click.png")
    with Image.open(path) as image:
        draw = ImageDraw.Draw(image)
        scale_x = image.width / 1440
        scale_y = image.height / 960
        box = [x * scale_x, y * scale_y, (x + width) * scale_x, (y + height) * scale_y]
        draw.rectangle(box, outline=(255, 56, 56), width=5)
        label = f"click {index}"
        font = ImageFont.load_default()
        label_box = draw.textbbox((0, 0), label, font=font)
        label_width = label_box[2] - label_box[0] + 10
        label_height = label_box[3] - label_box[1] + 8
        label_x = max(0, box[0])
        label_y = max(0, box[1] - label_height)
        draw.rectangle(
            [label_x, label_y, label_x + label_width, label_y + label_height],
            fill=(255, 56, 56),
        )
        draw.text((label_x + 5, label_y + 4), label, fill=(255, 255, 255), font=font)
        image.save(annotated_path)
    return str(annotated_path)


def _extract_reasoning(item: Any) -> str:
    model_output = getattr(item, "model_output", None)
    if not model_output:
        return "未捕获推理摘要。"
    current_state = getattr(model_output, "current_state", None)
    if current_state:
        return (
            f"上一步评估：{getattr(current_state, 'evaluation_previous_goal', '')}；"
            f"下一步目标：{getattr(current_state, 'next_goal', '')}"
        )
    return "未捕获推理摘要。"


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
