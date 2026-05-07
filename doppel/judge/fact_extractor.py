from __future__ import annotations

import json
import re
from pathlib import Path

from doppel.judge.schema import Fact
from doppel.runtime.models import StepEvent

POSITION_PATTERNS = [
    r"(?:这是|这是一个|页面显示这是|产品是|应用是|网站是|Zao 是|早播是)([^。；\n]{6,80})",
    r"(?:产品定位|核心价值|主要价值|核心功能)[：:，,]?([^。；\n]{6,100})",
    r"(?:提供|面向|适合)([^。；\n]{6,80})",
]

MAIN_ACTION_TOKENS = [
    "下载",
    "开始",
    "开始使用",
    "注册",
    "登录",
    "试用",
    "立即体验",
    "获取",
    "安装",
    "预约",
    "搜索",
    "分类",
    "热门工具",
    "推荐",
    "工具入口",
    "提交",
]

TRUST_SIGNAL_KEYWORDS = {
    "评分": ["评分", "rating"],
    "用户评价": ["评价", "评论", "用户心声", "用户反馈", "reviews", "testimonial"],
    "品牌背书": ["公司", "开发", "官方", "品牌", "备案", "关于我们", "公众号", "社区", "联系", "作者", "来源"],
    "安全隐私": ["安全", "隐私", "认证", "加密", "保障", "用户协议", "隐私政策"],
    "应用商店": ["app store", "应用商店", "google play"],
    "内容维护": ["更新", "收录", "最新", "每日", "提交工具", "站点说明", "友情链接", "教程", "白皮书"],
}


class FactExtractor:
    def extract(self, *, steps: list[StepEvent], stop_reason: str) -> list[Fact]:
        step_ids = [step.step_id for step in steps]
        screenshot_count = len([step for step in steps if step.screenshot_path])
        screenshots = _screenshots_for_steps(steps)
        facts = [
            Fact(
                fact_id="fact_step_count",
                type="step_count",
                statement=f"本次运行记录了 {len(steps)} 个步骤。",
                evidence_step_ids=step_ids,
                evidence_screenshots=list(screenshots.values()),
                data={"count": len(steps)},
                confidence=1.0,
            ),
            Fact(
                fact_id="fact_stop_reason",
                type="stop_reason",
                statement=f"本次运行停止原因是「{stop_reason}」。",
                evidence_step_ids=step_ids[-1:] if step_ids else [],
                evidence_screenshots=_fact_screenshots(step_ids[-1:] if step_ids else [], screenshots),
                data={"stop_reason": stop_reason},
                confidence=1.0,
            ),
            Fact(
                fact_id="fact_screenshot_count",
                type="screenshot_count",
                statement=f"本次运行捕获了 {screenshot_count} 张截图。",
                evidence_step_ids=step_ids,
                evidence_screenshots=list(screenshots.values()),
                data={"count": screenshot_count},
                confidence=1.0,
            ),
        ]
        if steps:
            facts.append(
                Fact(
                    fact_id="fact_last_action",
                    type="last_action",
                    statement=f"最后记录的动作是「{steps[-1].action_type}」。",
                    evidence_step_ids=[steps[-1].step_id],
                    evidence_screenshots=_fact_screenshots([steps[-1].step_id], screenshots),
                    data={"action_type": steps[-1].action_type},
                    confidence=1.0,
                )
            )
        facts.extend(_extract_judgement_facts(steps, screenshots))
        return facts

    def write(self, artifact_dir: Path, facts: list[Fact]) -> Path:
        path = artifact_dir / "facts.json"
        path.write_text(
            json.dumps([fact.model_dump(mode="json") for fact in facts], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path


def _extract_judgement_facts(steps: list[StepEvent], screenshots: dict[int, str]) -> list[Fact]:
    facts: list[Fact] = []
    first_content = _first_content_step(steps)
    if first_content:
        facts.append(
            Fact(
                fact_id="fact_first_content_step",
                type="first_content_step",
                statement=f"第一个非空白页面出现在步骤 {first_content.step_id}。",
                evidence_step_ids=[first_content.step_id],
                evidence_screenshots=_fact_screenshots([first_content.step_id], screenshots),
                data={"step_id": first_content.step_id, "url": first_content.url},
                confidence=1.0,
            )
        )

    first_click = _first_step_by_action(steps, "click")
    if first_click:
        click_target = _click_target(first_click)
        facts.extend(
            [
                Fact(
                    fact_id="fact_first_click_step",
                    type="first_click_step",
                    statement=f"首次点击发生在步骤 {first_click.step_id}。",
                    evidence_step_ids=[first_click.step_id],
                    evidence_screenshots=_fact_screenshots([first_click.step_id], screenshots),
                    data={"step_id": first_click.step_id},
                    confidence=1.0,
                ),
                Fact(
                    fact_id="fact_click_target",
                    type="click_target",
                    statement=f"首次点击目标是「{click_target}」。",
                    evidence_step_ids=[first_click.step_id],
                    evidence_screenshots=_fact_screenshots([first_click.step_id], screenshots),
                    data={"target": click_target, "is_primary": _is_primary_action_target(click_target)},
                    confidence=0.85,
                ),
            ]
        )

    scroll_steps = [step for step in steps if step.action_type == "scroll"]
    scroll_discoveries = _scroll_discoveries(steps, scroll_steps)
    facts.append(
        Fact(
            fact_id="fact_scroll_count",
            type="scroll_count",
            statement=f"本次运行共滚动 {len(scroll_steps)} 次。",
            evidence_step_ids=[step.step_id for step in scroll_steps],
            evidence_screenshots=_fact_screenshots([step.step_id for step in scroll_steps], screenshots),
            data={"count": len(scroll_steps), "directions": [_scroll_direction(step) for step in scroll_steps]},
            confidence=1.0,
        )
    )
    if scroll_discoveries:
        evidence_ids = [item["step_id"] for item in scroll_discoveries]
        facts.append(
            Fact(
                fact_id="fact_scroll_discoveries",
                type="scroll_discoveries",
                statement="滚动后发现：" + "；".join(item["summary"] for item in scroll_discoveries),
                evidence_step_ids=evidence_ids,
                evidence_screenshots=_fact_screenshots(evidence_ids, screenshots),
                data={"discoveries": scroll_discoveries},
                confidence=0.8,
            )
        )

    understanding = _understanding_fact(steps)
    if understanding:
        facts.extend(
            [
                Fact(
                    fact_id="fact_understanding_step",
                    type="understanding_step",
                    statement=f"Agent 首次表达产品理解发生在步骤 {understanding['step_id']}。",
                    evidence_step_ids=[understanding["step_id"]],
                    evidence_screenshots=_fact_screenshots([understanding["step_id"]], screenshots),
                    data={"step_id": understanding["step_id"]},
                    confidence=0.8,
                ),
                Fact(
                    fact_id="fact_understanding_summary",
                    type="understanding_summary",
                    statement=f"Agent 对产品定位的理解：{understanding['summary']}。",
                    evidence_step_ids=[understanding["step_id"]],
                    evidence_screenshots=_fact_screenshots([understanding["step_id"]], screenshots),
                    data={"summary": understanding["summary"]},
                    confidence=0.8,
                ),
            ]
        )

    trust_signals = _trust_signals(steps)
    facts.append(
        Fact(
            fact_id="fact_trust_signals",
            type="trust_signals",
            statement=_trust_signal_statement(trust_signals),
            evidence_step_ids=trust_signals["step_ids"],
            evidence_screenshots=_fact_screenshots(trust_signals["step_ids"], screenshots),
            data=trust_signals,
            confidence=0.75,
        )
    )

    redundant = _redundant_steps(steps)
    facts.append(
        Fact(
            fact_id="fact_redundant_steps",
            type="redundant_steps",
            statement=_redundant_statement(redundant),
            evidence_step_ids=redundant["step_ids"],
            evidence_screenshots=_fact_screenshots(redundant["step_ids"], screenshots),
            data=redundant,
            confidence=0.85,
        )
    )
    return facts


def _first_content_step(steps: list[StepEvent]) -> StepEvent | None:
    for step in steps:
        if step.url and step.url != "about:blank":
            return step
    return None


def _first_step_by_action(steps: list[StepEvent], action_type: str) -> StepEvent | None:
    for step in steps:
        if step.action_type == action_type:
            return step
    return None


def _click_target(step: StepEvent) -> str:
    text = "；".join(filter(None, [step.target_description, step.action_input, step.reasoning_summary]))
    quoted = re.findall(r"[「'“\"]([^」'”\"]{1,40})[」'”\"]", text)
    for item in quoted:
        if _is_primary_action_target(item):
            return item
    search_intent = re.search(r"(?:点击|选择|进入|验证)([^，。；\n]{0,30}搜索框)", text, flags=re.I)
    if search_intent:
        return _compact_click_target(search_intent.group(1))
    intent = re.search(
        r"(?:点击|选择|进入|验证)(?:页面上的|首屏的)?([^，。；\n]{2,40}?)(?:链接|按钮|入口|分类|搜索框|标签|路径)",
        text,
        flags=re.I,
    )
    if intent:
        return _compact_click_target(intent.group(1))
    if step.target_description and not re.fullmatch(r"click:\s*\{[^}]+\}", step.target_description):
        return step.target_description
    match = re.search(
        r"(站内AI工具搜索|AI图像工具|AI写作工具|AI视频工具|AI办公工具|AI聊天助手|AI编程工具|热门工具|"
        r"立即下载|开始使用|注册|登录|下载|试用|安装|预约|App Store|搜索框|搜索|分类入口)",
        text,
        flags=re.I,
    )
    return match.group(1) if match else (step.target_description or "未知点击目标")


def _compact_click_target(target: str) -> str:
    cleaned = re.sub(r"^(?:了|到|页面上|页面中的|首屏的|一个|这个|该)", "", target).strip(" ：:「」'“”")
    cleaned = cleaned.replace("'", "").replace('"', "")
    return cleaned[:40] if cleaned else target[:40]


def _is_primary_action_target(target: str) -> bool:
    normalized = target.lower()
    return any(token.lower() in normalized for token in MAIN_ACTION_TOKENS) or bool(re.search(r"ai.+工具", target, flags=re.I))


def _scroll_direction(step: StepEvent) -> str:
    text = f"{step.target_description or ''} {step.action_input or ''}".lower()
    if "down" in text or "向下" in text:
        return "down"
    if "up" in text or "向上" in text:
        return "up"
    return "unknown"


def _scroll_discoveries(steps: list[StepEvent], scroll_steps: list[StepEvent]) -> list[dict[str, object]]:
    by_id = {step.step_id: step for step in steps}
    discoveries: list[dict[str, object]] = []
    for scroll in scroll_steps:
        target = by_id.get(scroll.step_id + 1, scroll)
        summary = _compact_summary(target.reasoning_summary or target.observation_summary)
        if _has_meaningful_discovery(summary):
            discoveries.append(
                {
                    "scroll_step_id": scroll.step_id,
                    "step_id": target.step_id,
                    "direction": _scroll_direction(scroll),
                    "summary": summary,
                }
            )
    return discoveries


def _understanding_fact(steps: list[StepEvent]) -> dict[str, object] | None:
    for step in steps:
        summary = _extract_position_summary(_step_text(step))
        if summary:
            return {"step_id": step.step_id, "summary": summary}
    return None


def _extract_position_summary(text: str) -> str | None:
    for pattern in POSITION_PATTERNS:
        match = re.search(pattern, text, flags=re.I)
        if match:
            summary = _compact_summary(match.group(0))
            summary = summary.split("，由", 1)[0]
            if len(summary) >= 8 and _is_position_summary(summary):
                return summary
    return None


def _is_position_summary(summary: str) -> bool:
    concrete_tokens = ["应用", "平台", "产品", "服务", "网站", "工具", "播客", "AI", "内容", "音频"]
    generic_only_tokens = ["核心价值、功能特点", "用户反馈", "更多产品功能介绍", "主要行动入口"]
    return any(token in summary for token in concrete_tokens) and not any(token in summary for token in generic_only_tokens)


def _trust_signals(steps: list[StepEvent]) -> dict[str, object]:
    found: dict[str, list[int]] = {}
    for step in steps:
        text = _step_text(step).lower()
        for signal_type, keywords in TRUST_SIGNAL_KEYWORDS.items():
            has_keyword = any(keyword.lower() in text for keyword in keywords)
            has_score = signal_type == "评分" and re.search(r"[1-5](?:\.\d)?\s*分", text)
            if has_keyword or has_score:
                found.setdefault(signal_type, []).append(step.step_id)
    step_ids = sorted({step_id for ids in found.values() for step_id in ids})
    return {"types": sorted(found.keys()), "count": len(found), "step_ids": step_ids}


def _redundant_steps(steps: list[StepEvent]) -> dict[str, object]:
    redundant_ids: list[int] = []
    types: set[str] = set()
    max_wait_run = 0
    current_action = None
    current_run: list[StepEvent] = []
    for step in steps:
        if step.action_type == current_action:
            current_run.append(step)
        else:
            _mark_redundant_run(current_run, redundant_ids, types)
            current_action = step.action_type
            current_run = [step]
        if step.action_type == "wait":
            max_wait_run = max(max_wait_run, len(current_run))
    _mark_redundant_run(current_run, redundant_ids, types)
    return {
        "count": len(sorted(set(redundant_ids))),
        "step_ids": sorted(set(redundant_ids)),
        "types": sorted(types),
        "max_consecutive_wait": max_wait_run,
        "severe": max_wait_run > 5,
    }


def _mark_redundant_run(run: list[StepEvent], redundant_ids: list[int], types: set[str]) -> None:
    if len(run) <= 1:
        return
    action = run[0].action_type
    if action == "wait":
        redundant_ids.extend(step.step_id for step in run[1:])
        types.add("连续等待")
    elif action == "scroll" and len(run) > 2:
        redundant_ids.extend(step.step_id for step in run[2:])
        types.add("连续滚动")


def _step_text(step: StepEvent) -> str:
    return "；".join(
        filter(
            None,
            [
                step.page_title,
                step.url,
                step.observation_summary,
                step.reasoning_summary,
                step.target_description,
                step.action_input,
                step.error_message,
            ],
        )
    )


def _compact_summary(text: str, limit: int = 80) -> str:
    normalized = re.sub(r"\s+", " ", text).strip(" ；。")
    normalized = re.sub(r"^上一步评估[:：]?", "", normalized).strip(" ；。")
    return normalized[:limit]


def _has_meaningful_discovery(summary: str) -> bool:
    negative_tokens = ["仍在加载", "空白", "没有显示", "未发现", "重复", "无内容"]
    positive_tokens = ["显示", "发现", "功能", "价值", "评价", "入口", "下载", "内容", "产品", "页面"]
    return any(token in summary for token in positive_tokens) and not any(token in summary for token in negative_tokens)


def _trust_signal_statement(trust_signals: dict[str, object]) -> str:
    types = trust_signals["types"]
    if types:
        return "页面出现信任信号：" + "、".join(types) + "。"
    return "页面未发现明显信任信号。"


def _redundant_statement(redundant: dict[str, object]) -> str:
    if redundant["count"]:
        return f"检测到 {redundant['count']} 个冗余步骤，类型：{'、'.join(redundant['types'])}。"
    return "未检测到明显冗余步骤。"


def _screenshots_for_steps(steps: list[StepEvent]) -> dict[int, str]:
    return {step.step_id: step.screenshot_path for step in steps if step.screenshot_path}


def _fact_screenshots(step_ids: list[int], screenshots: dict[int, str]) -> list[str]:
    return [screenshots[step_id] for step_id in step_ids if step_id in screenshots]
