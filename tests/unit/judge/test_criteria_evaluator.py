from doppel.config.models import JudgeCriterion
from doppel.judge.criteria_evaluator import CriteriaEvaluator
from doppel.judge.schema import Fact


def test_criteria_evaluator_scores_path_efficiency() -> None:
    criteria = [
        JudgeCriterion(
            id="path_efficiency",
            question="How direct was the path?",
            good="Reached quickly",
            bad="Got lost",
        )
    ]
    facts = [
        Fact(
            fact_id="fact_step_count",
            type="step_count",
            statement="本次运行记录了 3 个步骤。",
            evidence_step_ids=[1, 2, 3],
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_stop_reason",
            type="stop_reason",
            statement="本次运行停止原因是「mission_completed」。",
            evidence_step_ids=[3],
            confidence=1.0,
        ),
    ]

    evaluations = CriteriaEvaluator().evaluate(criteria=criteria, facts=facts)

    assert evaluations[0].criterion_id == "path_efficiency"
    assert evaluations[0].result == "pass"


def test_criteria_evaluator_uses_specific_judgement_facts() -> None:
    criteria = [
        JudgeCriterion(id="first_screen_clarity", question="Clear?", good="Clear", bad="Unclear"),
        JudgeCriterion(id="primary_action", question="CTA?", good="Found", bad="Missing"),
        JudgeCriterion(id="scroll_discovery", question="Scroll?", good="Useful", bad="Repeated"),
        JudgeCriterion(id="path_efficiency", question="Path?", good="Short", bad="Long"),
        JudgeCriterion(id="trust_and_confidence", question="Trust?", good="Trusted", bad="No trust"),
    ]
    facts = [
        Fact(
            fact_id="fact_step_count",
            type="step_count",
            statement="本次运行记录了 4 个步骤。",
            evidence_step_ids=[1, 2, 3, 4],
            evidence_screenshots=["screenshots/step-004.png"],
            data={"count": 4},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_stop_reason",
            type="stop_reason",
            statement="本次运行停止原因是「mission_completed」。",
            evidence_step_ids=[4],
            data={"stop_reason": "mission_completed"},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_first_content_step",
            type="first_content_step",
            statement="第一个非空白页面出现在步骤 2。",
            evidence_step_ids=[2],
            evidence_screenshots=["screenshots/step-002.png"],
            data={"step_id": 2},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_understanding_step",
            type="understanding_step",
            statement="Agent 首次表达产品理解发生在步骤 2。",
            evidence_step_ids=[2],
            evidence_screenshots=["screenshots/step-002.png"],
            data={"step_id": 2},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_understanding_summary",
            type="understanding_summary",
            statement="Agent 对产品定位的理解：AI 播客应用。",
            evidence_step_ids=[2],
            evidence_screenshots=["screenshots/step-002.png"],
            data={"summary": "这是一个 AI 播客应用"},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_first_click_step",
            type="first_click_step",
            statement="首次点击发生在步骤 3。",
            evidence_step_ids=[3],
            evidence_screenshots=["screenshots/step-003.png"],
            data={"step_id": 3},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_click_target",
            type="click_target",
            statement="首次点击目标是「立即下载」。",
            evidence_step_ids=[3],
            evidence_screenshots=["screenshots/step-003.png"],
            data={"target": "立即下载", "is_primary": True},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_scroll_count",
            type="scroll_count",
            statement="本次运行共滚动 1 次。",
            evidence_step_ids=[2],
            evidence_screenshots=["screenshots/step-002.png"],
            data={"count": 1, "directions": ["down"]},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_scroll_discoveries",
            type="scroll_discoveries",
            statement="滚动后发现：功能介绍。",
            evidence_step_ids=[3],
            evidence_screenshots=["screenshots/step-003.png"],
            data={"discoveries": [{"step_id": 3, "summary": "发现功能介绍和用户评价"}]},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_trust_signals",
            type="trust_signals",
            statement="页面出现信任信号：评分、用户评价、应用商店。",
            evidence_step_ids=[3],
            evidence_screenshots=["screenshots/step-003.png"],
            data={"types": ["评分", "用户评价", "应用商店"], "count": 3, "step_ids": [3]},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_redundant_steps",
            type="redundant_steps",
            statement="未检测到明显冗余步骤。",
            evidence_step_ids=[],
            data={"count": 0, "types": [], "max_consecutive_wait": 0, "severe": False},
            confidence=1.0,
        ),
    ]

    evaluations = {item.criterion_id: item for item in CriteriaEvaluator().evaluate(criteria=criteria, facts=facts)}

    assert evaluations["first_screen_clarity"].summary.startswith("步骤 2 首屏加载成功")
    assert evaluations["primary_action"].summary == "步骤 3 成功识别并点击主要入口「立即下载」，入口明显且易于理解"
    assert evaluations["scroll_discovery"].result == "pass"
    assert evaluations["path_efficiency"].result == "pass"
    assert evaluations["trust_and_confidence"].result == "pass"
    assert evaluations["first_screen_clarity"].evidence_screenshots == ["screenshots/step-002.png"]


def test_criteria_evaluator_adds_suggestion_for_failures() -> None:
    criteria = [JudgeCriterion(id="first_screen_clarity", question="Clear?", good="Clear", bad="Slow")]
    facts = [
        Fact(
            fact_id="fact_first_content_step",
            type="first_content_step",
            statement="第一个非空白页面出现在步骤 6。",
            evidence_step_ids=[6],
            evidence_screenshots=["screenshots/step-006.png"],
            data={"step_id": 6},
            confidence=1.0,
        )
    ]

    evaluation = CriteriaEvaluator().evaluate(criteria=criteria, facts=facts)[0]

    assert evaluation.result == "fail"
    assert "用了 6 步" in evaluation.summary
    assert evaluation.improvement_suggestion
    assert evaluation.evidence_screenshots == ["screenshots/step-006.png"]


def test_criteria_evaluator_maps_custom_criterion_aliases() -> None:
    criteria = [
        JudgeCriterion(
            id="designer_aesthetic_review",
            question="设计师是否能从视觉布局判断站点质量？",
            good="视觉层级清晰",
            bad="布局混乱",
        ),
        JudgeCriterion(
            id="tool_discovery_entry",
            question="是否有明确搜索或分类入口？",
            good="入口明确",
            bad="入口分散",
        ),
    ]
    facts = [
        Fact(
            fact_id="fact_step_count",
            type="step_count",
            statement="本次运行记录了 3 个步骤。",
            evidence_step_ids=[1, 2, 3],
            evidence_screenshots=["screenshots/step-003.png"],
            data={"count": 3},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_stop_reason",
            type="stop_reason",
            statement="本次运行停止原因是「mission_completed」。",
            evidence_step_ids=[3],
            data={"stop_reason": "mission_completed"},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_first_content_step",
            type="first_content_step",
            statement="第一个非空白页面出现在步骤 1。",
            evidence_step_ids=[1],
            evidence_screenshots=["screenshots/step-001.png"],
            data={"step_id": 1},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_understanding_summary",
            type="understanding_summary",
            statement="Agent 对产品定位的理解：AI 工具导航站。",
            evidence_step_ids=[1],
            evidence_screenshots=["screenshots/step-001.png"],
            data={"summary": "这是一个 AI 工具导航站"},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_first_click_step",
            type="first_click_step",
            statement="首次点击发生在步骤 2。",
            evidence_step_ids=[2],
            evidence_screenshots=["screenshots/step-002.png"],
            data={"step_id": 2},
            confidence=1.0,
        ),
        Fact(
            fact_id="fact_click_target",
            type="click_target",
            statement="首次点击目标是「搜索框」。",
            evidence_step_ids=[2],
            evidence_screenshots=["screenshots/step-002.png"],
            data={"target": "搜索框", "is_primary": True},
            confidence=1.0,
        ),
    ]

    evaluations = {item.criterion_id: item for item in CriteriaEvaluator().evaluate(criteria=criteria, facts=facts)}

    assert evaluations["designer_aesthetic_review"].result == "partial"
    assert "视觉" in evaluations["designer_aesthetic_review"].summary
    assert evaluations["tool_discovery_entry"].result == "pass"
