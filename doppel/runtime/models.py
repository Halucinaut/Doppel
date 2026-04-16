from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ActionType = Literal["click", "input", "scroll", "wait", "stop"]


class PerceptionInput(BaseModel):
    screenshot_path: str
    url: str
    page_title: str | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    history_summary: str | None = None


class Action(BaseModel):
    action_type: ActionType
    target_description: str | None = None
    text: str | None = None
    x: int | None = None
    y: int | None = None
    stop_reason: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "Action":
        if self.action_type == "input" and not self.text:
            raise ValueError("input action requires text")
        if self.action_type == "stop" and not self.stop_reason:
            raise ValueError("stop action requires stop_reason")
        return self


class StepEvent(BaseModel):
    step_id: int = Field(ge=1)
    timestamp: str
    url: str
    page_title: str | None = None
    action_type: ActionType
    action_input: str | None = None
    target_description: str | None = None
    observation_summary: str
    reasoning_summary: str
    screenshot_path: str
    elapsed_ms: int = Field(ge=0)
    status: Literal["ok", "error", "stopped"]
    error_message: str | None = None
