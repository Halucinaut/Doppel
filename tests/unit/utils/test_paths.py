from pathlib import Path

from doppel.utils.paths import browser_use_env, resolve_playwright_executable


def test_resolve_playwright_executable_finds_workspace_browser() -> None:
    executable = resolve_playwright_executable(project_root=Path.cwd())
    assert executable is not None
    assert "Google Chrome for Testing" in str(executable) or "chrome-headless-shell" in str(executable)


def test_browser_use_env_points_inside_project(tmp_path: Path) -> None:
    env = browser_use_env(tmp_path)
    assert env["BROWSER_USE_CONFIG_DIR"] == str(tmp_path / ".browseruse")
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path / ".playwright-browsers")
