from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Fact(BaseModel):
    fact_id: str
    type: str
    statement: str
    evidence_step_ids: list[int] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class Evaluation(BaseModel):
    criterion_id: str
    result: Literal["pass", "partial", "fail"]
    summary: str
    evidence_fact_ids: list[str] = Field(default_factory=list)
    evidence_step_ids: list[int] = Field(default_factory=list)
