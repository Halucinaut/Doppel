from __future__ import annotations

import os
from pathlib import Path


def resolve_playwright_executable(project_root: Path | None = None, prefer_headless_shell: bool = False) -> Path | None:
    root = (project_root or Path.cwd()) / ".playwright-browsers"
    if not root.exists():
        return None

    if prefer_headless_shell:
        candidates = sorted(
            root.glob("chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell"),
            reverse=True,
        )
        if candidates:
            return candidates[0]

    candidates = sorted(
        root.glob("chromium-*/chrome-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"),
        reverse=True,
    )
    if candidates:
        return candidates[0]

    if not prefer_headless_shell:
        return resolve_playwright_executable(project_root=project_root, prefer_headless_shell=True)
    return None


def browser_use_env(project_root: Path | None = None) -> dict[str, str]:
    root = project_root or Path.cwd()
    config_dir = root / ".browseruse"
    config_dir.mkdir(parents=True, exist_ok=True)
    return {
        "BROWSER_USE_CONFIG_DIR": str(config_dir),
        "PLAYWRIGHT_BROWSERS_PATH": str(root / ".playwright-browsers"),
        **{k: v for k, v in os.environ.items() if k.endswith("_API_KEY")},
    }
