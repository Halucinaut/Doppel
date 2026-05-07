from pathlib import Path

from doppel.browser.browser_use_client import _build_browser_use_task
from doppel.config.loader import build_run_spec
from doppel.sandbox.remote import RemoteUrlSandbox


def test_build_browser_use_task_discourages_domain_guessing(tmp_path: Path) -> None:
    product = tmp_path / "product.yaml"
    product.write_text(
        "\n".join(
            [
                'name: "Example Domain"',
                'entry_url: "https://example.com"',
                'description: "A simple static webpage"',
            ]
        ),
        encoding="utf-8",
    )
    skill = tmp_path / "skill.yaml"
    skill.write_text(
        "\n".join(
            [
                'name: "Landing page check"',
                'version: "1.0"',
                'persona: "newcomer"',
                'mission: "Understand the page and identify the main visible link."',
                "stop_conditions:",
                '  - "Understands the page"',
                "judge_criteria:",
                '  - id: "clarity"',
                '    question: "Was the page understandable?"',
                '    good: "Clear"',
                '    bad: "Confusing"',
            ]
        ),
        encoding="utf-8",
    )

    spec = build_run_spec(product, skill)
    ctx = RemoteUrlSandbox(artifact_root=tmp_path / ".doppel" / "runs").prepare(spec)

    task = _build_browser_use_task(spec, ctx)

    assert "必须从给定入口 URL 开始，并把它视为唯一可信入口。" in task
    assert "不要只根据产品名称猜测或编造其他域名。" in task
