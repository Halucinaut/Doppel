from pathlib import Path

from doppel.browser.playwright_adapter import PlaywrightBrowserAdapter
from doppel.runtime.models import Action


HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Doppel Fixture</title>
  </head>
  <body>
    <button id="cta" style="margin: 40px; width: 160px; height: 50px;" onclick="document.title='Clicked'; document.body.setAttribute('data-clicked', 'true');">
      Start Free
    </button>
  </body>
</html>
"""


def test_playwright_adapter_opens_observes_and_clicks(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.html"
    fixture.write_text(HTML, encoding="utf-8")
    screenshot1 = tmp_path / "shot-1.png"
    screenshot2 = tmp_path / "shot-2.png"
    adapter = PlaywrightBrowserAdapter(project_root=Path.cwd())

    try:
        adapter.open(fixture.resolve().as_uri())
        perception = adapter.observe(screenshot1)
        adapter.execute(Action(action_type="click", x=120, y=65, target_description="Start Free button"))
        perception_after = adapter.observe(screenshot2)
    finally:
        adapter.close()

    assert screenshot1.exists()
    assert screenshot2.exists()
    assert perception.page_title == "Doppel Fixture"
    assert perception_after.page_title == "Clicked"
