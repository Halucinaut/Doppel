from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from doppel.config.models import JudgeCriterion
from doppel.judge.schema import Evaluation, Fact


class CriteriaEvaluator:
    def evaluate(self, *, criteria: list[JudgeCriterion], facts: list[Fact]) -> list[Evaluation]:
        store = _FactStore(facts)
        evaluations = []

        for criterion in criteria:
            evaluations.append(self._evaluate_single(criterion, store))
        return evaluations

    def write(self, artifact_dir: Path, evaluations: list[Evaluation]) -> Path:
        path = artifact_dir / "evaluation.json"
        path.write_text(
            json.dumps(
                [evaluation.model_dump(mode="json") for evaluation in evaluations],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def _evaluate_single(self, criterion: JudgeCriterion, store: "_FactStore") -> Evaluation:
        criterion_id = criterion.id.lower()
        if criterion_id == "first_screen_clarity":
            return _evaluate_first_screen(criterion.id, store)
        if criterion_id == "primary_action":
            return _evaluate_primary_action(criterion.id, store)
        if criterion_id == "scroll_discovery":
            return _evaluate_scroll_discovery(criterion.id, store)
        if criterion_id == "path_efficiency":
            return _evaluate_path_efficiency(criterion.id, store)
        if criterion_id == "trust_and_confidence":
            return _evaluate_trust(criterion.id, store)

        normalized = _normalized_criterion_text(criterion)
        if _is_visual_criterion(criterion):
            return _evaluate_visual_experience(criterion.id, store)
        if _has_any(normalized, ["first_screen_clarity", "screen", "clarity", "首屏", "清晰", "定位"]):
            return _evaluate_first_screen(criterion.id, store)
        if _has_any(normalized, ["primary_action", "action", "cta", "entry", "入口", "行动", "搜索", "分类", "转化"]):
            return _evaluate_primary_action(criterion.id, store)
        if _has_any(normalized, ["scroll_discovery", "scroll", "下滑", "滚动", "信息递进", "长页面"]):
            return _evaluate_scroll_discovery(criterion.id, store)
        if _has_any(normalized, ["path_efficiency", "path", "efficiency", "路径", "效率", "步骤"]):
            return _evaluate_path_efficiency(criterion.id, store)
        if _has_any(normalized, ["trust_and_confidence", "trust", "confidence", "信任", "可信", "信心"]):
            return _evaluate_trust(criterion.id, store)
        return _evaluate_generic(criterion.id, store)


class _FactStore:
    def __init__(self, facts: list[Fact]) -> None:
        self.facts = facts
        self.by_id = {fact.fact_id: fact for fact in facts}

    def fact(self, fact_id: str) -> Fact | None:
        return self.by_id.get(fact_id)

    def data(self, fact_id: str) -> dict[str, Any]:
        fact = self.fact(fact_id)
        return fact.data if fact else {}

    def step_count(self) -> int:
        data_count = self.data("fact_step_count").get("count")
        if isinstance(data_count, int):
            return data_count
        fact = self.fact("fact_step_count")
        if fact:
            match = re.search(r"\d+", fact.statement)
            return int(match.group(0)) if match else 0
        return 0

    def stop_reason(self) -> str:
        reason = self.data("fact_stop_reason").get("stop_reason")
        if isinstance(reason, str):
            return reason
        fact = self.fact("fact_stop_reason")
        if fact:
            quoted = re.search(r"[「']([^」']+)[」']", fact.statement)
            return quoted.group(1) if quoted else "unknown"
        return "unknown"


def _evaluate_first_screen(criterion_id: str, store: _FactStore) -> Evaluation:
    fact_ids = ["fact_first_content_step", "fact_understanding_summary", "fact_understanding_step"]
    content_step = _int_data(store, "fact_first_content_step", "step_id")
    understanding = _str_data(store, "fact_understanding_summary", "summary")
    understanding_step = _int_data(store, "fact_understanding_step", "step_id")
    if content_step == 0:
        return _evaluation(
            criterion_id,
            "fail",
            "未识别到非空白首屏步骤，页面没有在评测过程中成功显示内容",
            fact_ids,
            store,
            "首屏未加载",
            "检查首屏资源加载、首包响应和单页应用初始化逻辑，避免新用户看到空白页。",
        )
    if content_step > 3:
        return _evaluation(
            criterion_id,
            "fail",
            f"首屏加载耗时过长，用了 {content_step} 步才显示内容，影响首次访问体验",
            fact_ids,
            store,
            f"步骤 {content_step} 首次显示内容",
            "优化首屏资源加载，减少阻塞脚本和初始化等待，让核心内容在 3 步内可见。",
        )
    if understanding and understanding_step == content_step:
        return _evaluation(
            criterion_id,
            "pass",
            f"步骤 {content_step} 首屏加载成功，Agent 理解产品为：{understanding}",
            fact_ids,
            store,
            f"步骤 {content_step} 首屏加载并形成理解",
        )
    return _evaluation(
        criterion_id,
        "partial",
        f"步骤 {content_step} 首屏加载成功，但页面信息不足以让 Agent 理解产品用途",
        fact_ids,
        store,
        f"步骤 {content_step} 首屏加载",
        "在首屏补充一句明确的产品定位、目标用户和核心价值，降低首次理解成本。",
    )


def _evaluate_primary_action(criterion_id: str, store: _FactStore) -> Evaluation:
    fact_ids = ["fact_first_click_step", "fact_click_target"]
    click_step = _int_data(store, "fact_first_click_step", "step_id")
    click_target = _str_data(store, "fact_click_target", "target") or "未知入口"
    is_primary = bool(store.data("fact_click_target").get("is_primary"))
    if click_step == 0:
        return _evaluation(
            criterion_id,
            "fail",
            "Agent 未进行任何点击操作即停止，页面缺乏明确的主要行动入口",
            fact_ids,
            store,
            "未找到主要行动入口",
            "突出首屏主按钮，使用下载、开始使用、注册等明确动词，并降低导航干扰。",
        )
    if is_primary:
        return _evaluation(
            criterion_id,
            "pass",
            f"步骤 {click_step} 成功识别并点击主要入口「{click_target}」，入口明显且易于理解",
            fact_ids,
            store,
            f"步骤 {click_step} 点击主要入口",
        )
    return _evaluation(
        criterion_id,
        "partial",
        f"步骤 {click_step} 点击了「{click_target}」，但主要入口不够突出导致 Agent 选择了其他路径",
        fact_ids,
        store,
        f"步骤 {click_step} 点击非主要入口",
        "强化主行动入口的视觉权重和文案指向，弱化次级链接对首次路径的干扰。",
    )


def _evaluate_scroll_discovery(criterion_id: str, store: _FactStore) -> Evaluation:
    fact_ids = ["fact_scroll_count", "fact_scroll_discoveries"]
    scroll_count = _int_data(store, "fact_scroll_count", "count")
    discoveries = store.data("fact_scroll_discoveries").get("discoveries", [])
    summaries = [str(item.get("summary")) for item in discoveries if isinstance(item, dict) and item.get("summary")]
    if scroll_count == 0:
        return _evaluation(
            criterion_id,
            "partial",
            "Agent 未发生滚动，无法验证首屏以下信息层次",
            fact_ids,
            store,
            "未触发滚动发现",
            "确保首屏能引导用户继续浏览，或让核心价值在首屏完整表达。",
        )
    if not summaries:
        return _evaluation(
            criterion_id,
            "fail",
            f"滚动 {scroll_count} 次后仍未发现有效信息递进，页面内容重复或断裂",
            fact_ids,
            store,
            f"{scroll_count} 次滚动无有效发现",
            "重组长页面结构，让每屏承载不同的信息任务，例如价值、功能、场景、信任证明。",
        )
    if scroll_count <= 3 and len(summaries) >= scroll_count:
        return _evaluation(
            criterion_id,
            "pass",
            f"通过 {scroll_count} 次滚动，Agent 依次发现了：{'；'.join(summaries)}，信息层次分明",
            fact_ids,
            store,
            f"{scroll_count} 次滚动完成信息递进",
        )
    return _evaluation(
        criterion_id,
        "partial",
        f"Agent 进行了 {scroll_count} 次滚动才获取足够信息，页面信息密度较低",
        fact_ids,
        store,
        f"{scroll_count} 次滚动后形成理解",
        "提高每屏信息密度，合并重复模块，把定位、功能、入口和信任信号前移。",
    )


def _evaluate_path_efficiency(criterion_id: str, store: _FactStore) -> Evaluation:
    fact_ids = [
        "fact_step_count",
        "fact_first_content_step",
        "fact_understanding_step",
        "fact_first_click_step",
        "fact_stop_reason",
        "fact_redundant_steps",
    ]
    step_count = store.step_count()
    redundant = store.data("fact_redundant_steps")
    redundant_count = int(redundant.get("count") or 0)
    redundant_types = [str(item) for item in redundant.get("types", [])]
    severe = bool(redundant.get("severe"))
    milestone_path = _milestone_path(store)
    if step_count <= 5 and redundant_count == 0:
        return _evaluation(
            criterion_id,
            "pass",
            f"路径高效，{step_count} 步内完成：{milestone_path}",
            fact_ids,
            store,
            milestone_path,
        )
    if step_count <= 5 and redundant_count > 0 and not severe:
        return _evaluation(
            criterion_id,
            "partial",
            f"路径可接受但存在优化空间，{step_count} 步完成，其中 {redundant_count} 步为冗余操作（{'、'.join(redundant_types) or '重复操作'}）",
            fact_ids,
            store,
            milestone_path,
            "减少重复动作，让每一步都推动用户理解或完成任务。",
        )
    if 6 <= step_count <= 10 and redundant_count > 0 and not severe:
        return _evaluation(
            criterion_id,
            "partial",
            f"路径可接受但存在优化空间，{step_count} 步完成，其中 {redundant_count} 步为冗余操作（{'、'.join(redundant_types) or '重复操作'}）",
            fact_ids,
            store,
            milestone_path,
            "减少重复等待和重复滚动，把首屏加载、产品理解和主入口发现压缩到更短路径。",
        )
    if step_count <= 10 and redundant_count == 0:
        return _evaluation(
            criterion_id,
            "partial",
            f"路径可接受但存在优化空间，{step_count} 步完成，其中 0 步为冗余操作（无明显重复动作）",
            fact_ids,
            store,
            milestone_path,
            "压缩用户理解路径，把关键定位、入口和信任信息前移。",
        )
    problem = _path_problem(step_count, redundant_count, redundant_types, severe)
    return _evaluation(
        criterion_id,
        "fail",
        f"路径低效，用了 {step_count} 步，主要问题：{problem}，建议优化：优化首屏加载速度，减少重复等待，并将主要行动入口前置",
        fact_ids,
        store,
        milestone_path,
        "优化首屏加载速度，减少重复等待，并将主要行动入口前置。",
    )


def _evaluate_trust(criterion_id: str, store: _FactStore) -> Evaluation:
    fact_ids = ["fact_trust_signals"]
    trust = store.data("fact_trust_signals")
    types = [str(item) for item in trust.get("types", [])]
    count = int(trust.get("count") or len(types))
    if count >= 3:
        return _evaluation(
            criterion_id,
            "pass",
            f"页面提供了充分的信任信号：{'、'.join(types)}，支持用户决策",
            fact_ids,
            store,
            "发现充分信任信号",
        )
    if 1 <= count <= 2:
        return _evaluation(
            criterion_id,
            "partial",
            f"页面提供了部分信任信号：{'、'.join(types)}，但不足以完全建立用户信心",
            fact_ids,
            store,
            "发现部分信任信号",
            "补充评分、用户评价、品牌背书、安全隐私说明或官方认证等信任信息。",
        )
    return _evaluation(
        criterion_id,
        "fail",
        "页面缺少信任信号（如评分、评价、品牌背书等），用户难以判断是否值得继续",
        fact_ids,
        store,
        "未发现信任信号",
        "增加可验证的评分、评价、品牌背书、安全隐私说明和应用商店入口。",
    )


def _evaluate_visual_experience(criterion_id: str, store: _FactStore) -> Evaluation:
    fact_ids = ["fact_first_content_step", "fact_understanding_summary", "fact_scroll_discoveries", "fact_step_count"]
    content_step = _int_data(store, "fact_first_content_step", "step_id")
    understanding = _str_data(store, "fact_understanding_summary", "summary")
    discoveries = store.data("fact_scroll_discoveries").get("discoveries", [])
    summaries = [str(item.get("summary")) for item in discoveries if isinstance(item, dict) and item.get("summary")]
    if content_step and understanding and summaries:
        return _evaluation(
            criterion_id,
            "pass",
            f"步骤 {content_step} 首屏形成产品理解，滚动后继续发现：{'；'.join(summaries[:3])}，视觉信息组织支持继续浏览",
            fact_ids,
            store,
            f"步骤 {content_step} 形成视觉与内容理解",
        )
    if content_step and understanding:
        return _evaluation(
            criterion_id,
            "partial",
            f"步骤 {content_step} 首屏可理解产品定位为：{understanding}，但缺少滚动后的视觉信息递进证据",
            fact_ids,
            store,
            f"步骤 {content_step} 首屏可理解",
            "补充首屏以下的结构化视觉模块，让用户看到分类、案例、价值或信任信息的递进。",
        )
    return _evaluation(
        criterion_id,
        "fail",
        "未捕获到足够的首屏理解或后续信息递进证据，无法证明视觉层级能帮助用户完成判断",
        fact_ids,
        store,
        "视觉理解证据不足",
        "强化首屏标题、分类层级、卡片信息密度和下滑引导，减少视觉噪音。",
    )


def _evaluate_generic(criterion_id: str, store: _FactStore) -> Evaluation:
    stop_reason = store.stop_reason()
    step_count = store.step_count()
    milestone_path = _milestone_path(store)
    if stop_reason == "mission_completed":
        result = "partial"
        summary = f"任务完成，共 {step_count} 步，路径为：{milestone_path}；该评判标准尚未映射到专用规则"
        suggestion = "为该标准补充可提取事实和专用评判规则。"
    elif stop_reason in {"capture_only", "prepared"}:
        result = "partial"
        summary = f"本次运行停在「{stop_reason}」，只有捕获证据，未形成完整任务路径"
        suggestion = "使用 browser-use 跑完整交互路径后再评判该标准。"
    else:
        result = "fail"
        summary = f"本次运行以「{stop_reason}」停止，无法完成该标准评判"
        suggestion = "先修复运行链路错误，再重新评判。"
    return _evaluation(
        criterion_id,
        result,
        summary,
        ["fact_stop_reason", "fact_step_count", "fact_first_content_step", "fact_understanding_summary"],
        store,
        f"停止原因 {stop_reason}",
        suggestion,
    )


def _normalized_criterion_text(criterion: JudgeCriterion) -> str:
    return " ".join([criterion.id, criterion.question, criterion.good, criterion.bad]).lower()


def _has_any(text: str, tokens: list[str]) -> bool:
    return any(token.lower() in text for token in tokens)


def _is_visual_criterion(criterion: JudgeCriterion) -> bool:
    target = f"{criterion.id} {criterion.question}".lower()
    return _has_any(target, ["design", "aesthetic", "visual", "layout", "美学", "视觉", "设计", "布局"])


def _evaluation(
    criterion_id: str,
    result: str,
    summary: str,
    fact_ids: list[str],
    store: _FactStore,
    key_milestone: str,
    improvement_suggestion: str | None = None,
) -> Evaluation:
    facts = [store.fact(fact_id) for fact_id in fact_ids if store.fact(fact_id)]
    return Evaluation(
        criterion_id=criterion_id,
        result=result,
        summary=summary,
        evidence_fact_ids=[fact.fact_id for fact in facts if fact],
        evidence_step_ids=_collect_step_ids([fact for fact in facts if fact]),
        evidence_screenshots=_collect_screenshots([fact for fact in facts if fact]),
        key_milestone=key_milestone,
        improvement_suggestion=improvement_suggestion if result != "pass" else None,
    )


def _int_data(store: _FactStore, fact_id: str, key: str) -> int:
    value = store.data(fact_id).get(key)
    return value if isinstance(value, int) else 0


def _str_data(store: _FactStore, fact_id: str, key: str) -> str:
    value = store.data(fact_id).get(key)
    return value if isinstance(value, str) else ""


def _collect_step_ids(facts: list[Fact]) -> list[int]:
    seen: list[int] = []
    for fact in facts:
        for step_id in fact.evidence_step_ids:
            if step_id not in seen:
                seen.append(step_id)
    return seen


def _collect_screenshots(facts: list[Fact]) -> list[str]:
    seen: list[str] = []
    for fact in facts:
        for path in fact.evidence_screenshots:
            if path and path not in seen:
                seen.append(path)
    return seen


def _milestone_path(store: _FactStore) -> str:
    milestones: list[str] = []
    first_content = _int_data(store, "fact_first_content_step", "step_id")
    understanding = _int_data(store, "fact_understanding_step", "step_id")
    click = _int_data(store, "fact_first_click_step", "step_id")
    stop_reason = store.stop_reason()
    if first_content:
        milestones.append(f"步骤 {first_content} 首屏加载")
    if understanding:
        milestones.append(f"步骤 {understanding} 理解产品")
    if click:
        milestones.append(f"步骤 {click} 找到主要入口")
    milestones.append(f"完成任务（{stop_reason}）")
    return " -> ".join(milestones)


def _path_problem(step_count: int, redundant_count: int, redundant_types: list[str], severe: bool) -> str:
    if severe:
        return "存在超过 5 次连续等待，首屏加载或页面就绪判断严重拖慢路径"
    if redundant_count:
        return f"包含 {redundant_count} 个冗余步骤（{'、'.join(redundant_types) or '重复操作'}）"
    return f"总步骤数 {step_count} 超过 10 步，首次理解和完成路径偏长"
