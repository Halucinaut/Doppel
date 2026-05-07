from doppel.judge.fact_extractor import FactExtractor
from doppel.runtime.models import StepEvent


def test_fact_extractor_builds_basic_facts() -> None:
    steps = [
        StepEvent(
            step_id=1,
            timestamp="2026-04-10T18:00:00Z",
            url="https://example.com",
            page_title="Home",
            action_type="stop",
            action_input=None,
            target_description="初始视口截图",
            observation_summary="观察到页面「Home」，URL：https://example.com",
            reasoning_summary="Agent 决定停止：capture_only",
            screenshot_path="screenshots/step-001.png",
            elapsed_ms=100,
            status="stopped",
        )
    ]

    facts = FactExtractor().extract(steps=steps, stop_reason="capture_only")

    assert len(facts) >= 3
    assert facts[0].fact_id == "fact_step_count"
    assert facts[1].fact_id == "fact_stop_reason"


def test_fact_extractor_builds_judgement_facts() -> None:
    steps = [
        StepEvent(
            step_id=1,
            timestamp="2026-04-10T18:00:00Z",
            url="about:blank",
            page_title="Empty",
            action_type="wait",
            observation_summary="空白页",
            reasoning_summary="页面仍在加载。",
            screenshot_path="",
            elapsed_ms=100,
            status="ok",
        ),
        StepEvent(
            step_id=2,
            timestamp="2026-04-10T18:00:01Z",
            url="https://example.com",
            page_title="Home",
            action_type="scroll",
            observation_summary="观察到首页",
            reasoning_summary="这是一个 AI 播客应用，主要价值是把碎片时间变成收听场景。下一步向下滚动。",
            screenshot_path="screenshots/step-002.png",
            elapsed_ms=100,
            status="ok",
        ),
        StepEvent(
            step_id=3,
            timestamp="2026-04-10T18:00:02Z",
            url="https://example.com",
            page_title="Home",
            action_type="click",
            target_description="立即下载",
            observation_summary="观察到功能介绍和用户评价",
            reasoning_summary="滚动后发现功能介绍、用户评价和 4.8 分评分。点击「立即下载」。",
            screenshot_path="screenshots/step-003.png",
            elapsed_ms=100,
            status="ok",
        ),
    ]

    facts = {fact.fact_id: fact for fact in FactExtractor().extract(steps=steps, stop_reason="mission_completed")}

    assert facts["fact_first_content_step"].data["step_id"] == 2
    assert facts["fact_click_target"].data["target"] == "立即下载"
    assert facts["fact_click_target"].data["is_primary"] is True
    assert facts["fact_scroll_count"].data["count"] == 1
    assert facts["fact_understanding_summary"].data["summary"]
    assert "用户评价" in facts["fact_trust_signals"].data["types"]


def test_fact_extractor_recovers_click_label_from_reasoning_and_done_text_trust() -> None:
    steps = [
        StepEvent(
            step_id=1,
            timestamp="2026-04-10T18:00:00Z",
            url="https://ai-bot.cn",
            page_title="ai-bot.cn",
            action_type="click",
            target_description="click: {'index': 70}",
            observation_summary="观察到 AI 工具集首页",
            reasoning_summary="页面显示搜索框和分类入口。下一步目标：点击搜索框，验证搜索功能是否可用。",
            screenshot_path="screenshots/step-001.png",
            elapsed_ms=100,
            status="ok",
        ),
        StepEvent(
            step_id=2,
            timestamp="2026-04-10T18:00:01Z",
            url="https://ai-bot.cn",
            page_title="ai-bot.cn",
            action_type="stop",
            target_description="done: {'text': '站点每日更新 AI 工具，包含关于我们、提交工具和 AI 教程资源。'}",
            observation_summary="观察到结果页",
            reasoning_summary="任务完成。",
            screenshot_path="screenshots/step-002.png",
            elapsed_ms=100,
            status="stopped",
        ),
    ]

    facts = {fact.fact_id: fact for fact in FactExtractor().extract(steps=steps, stop_reason="mission_completed")}

    assert facts["fact_click_target"].data["target"] == "搜索框"
    assert facts["fact_click_target"].data["is_primary"] is True
    assert "内容维护" in facts["fact_trust_signals"].data["types"]


def test_fact_extractor_treats_ai_tool_category_as_primary_action() -> None:
    steps = [
        StepEvent(
            step_id=1,
            timestamp="2026-04-10T18:00:00Z",
            url="https://ai-bot.cn",
            page_title="ai-bot.cn",
            action_type="click",
            target_description="click: {'index': 723}",
            observation_summary="观察到 AI 工具分类导航",
            reasoning_summary="下一步目标：点击页面中的'AI设计工具'链接，验证设计相关工具分类入口是否有效。",
            screenshot_path="screenshots/step-001.png",
            elapsed_ms=100,
            status="ok",
        )
    ]

    facts = {fact.fact_id: fact for fact in FactExtractor().extract(steps=steps, stop_reason="mission_completed")}

    assert facts["fact_click_target"].data["target"] == "AI设计工具"
    assert facts["fact_click_target"].data["is_primary"] is True
