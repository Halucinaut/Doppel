from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from doppel.runtime.models import Action, PerceptionInput


class BrowserAdapter(ABC):
    @abstractmethod
    def open(self, entry_url: str) -> None:
        """Open the target product entry page."""

    @abstractmethod
    def observe(self, screenshot_path: Path, history_summary: str | None = None) -> PerceptionInput:
        """Capture a visual observation of the current page."""

    @abstractmethod
    def execute(self, action: Action) -> None:
        """Execute an action against the current page."""

    @abstractmethod
    def close(self) -> None:
        """Close browser resources."""


class StubBrowserAdapter(BrowserAdapter):
    def __init__(
        self,
        *,
        current_url: str = "https://example.com",
        page_title: str = "Home",
        viewport_width: int = 1440,
        viewport_height: int = 900,
    ) -> None:
        self.current_url = current_url
        self.page_title = page_title
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.actions: list[Action] = []
        self.opened = False

    def open(self, entry_url: str) -> None:
        self.current_url = entry_url
        self.opened = True

    def observe(self, screenshot_path: Path, history_summary: str | None = None) -> PerceptionInput:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(b"")
        return PerceptionInput(
            screenshot_path=str(screenshot_path),
            url=self.current_url,
            page_title=self.page_title,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            history_summary=history_summary,
        )

    def execute(self, action: Action) -> None:
        self.actions.append(action)

    def close(self) -> None:
        self.opened = False
