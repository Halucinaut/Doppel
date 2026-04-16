from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from doppel.browser.adapter import BrowserAdapter
from doppel.runtime.models import Action, PerceptionInput
from doppel.utils.paths import resolve_playwright_executable


class PlaywrightBrowserAdapter(BrowserAdapter):
    def __init__(
        self,
        *,
        project_root: Path | None = None,
        headless: bool = True,
        slow_mo_ms: int = 0,
    ) -> None:
        self.project_root = project_root or Path.cwd()
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def open(self, entry_url: str) -> None:
        executable_path = resolve_playwright_executable(self.project_root, prefer_headless_shell=self.headless)
        if executable_path is None:
            raise RuntimeError("Playwright browser executable not found under .playwright-browsers")

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            executable_path=str(executable_path),
            headless=self.headless,
            slow_mo=self.slow_mo_ms,
        )
        self._context = self._browser.new_context()
        self._page = self._context.new_page()
        self._page.goto(entry_url, wait_until="domcontentloaded")

    def observe(self, screenshot_path: Path, history_summary: str | None = None) -> PerceptionInput:
        page = self._require_page()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=False)
        viewport = page.viewport_size or {}
        return PerceptionInput(
            screenshot_path=str(screenshot_path),
            url=page.url,
            page_title=page.title(),
            viewport_width=viewport.get("width"),
            viewport_height=viewport.get("height"),
            history_summary=history_summary,
        )

    def execute(self, action: Action) -> None:
        page = self._require_page()
        if action.action_type == "click":
            if action.x is None or action.y is None:
                raise ValueError("click action requires x/y coordinates for Playwright adapter")
            page.mouse.click(action.x, action.y)
        elif action.action_type == "input":
            if action.x is None or action.y is None or action.text is None:
                raise ValueError("input action requires x, y, and text for Playwright adapter")
            page.mouse.click(action.x, action.y)
            page.keyboard.type(action.text)
        elif action.action_type == "scroll":
            page.mouse.wheel(0, 600)
        elif action.action_type == "wait":
            page.wait_for_timeout(500)
        elif action.action_type == "stop":
            return
        else:
            raise ValueError(f"Unsupported action_type: {action.action_type}")

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def _require_page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser page is not initialized")
        return self._page
