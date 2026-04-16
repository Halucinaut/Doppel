from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class AuthConfig(BaseModel):
    required: bool = False
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def validate_required_credentials(self) -> "AuthConfig":
        if self.required and (not self.username or not self.password):
            raise ValueError("auth.username and auth.password are required when auth.required is true")
        return self


class ResetConfig(BaseModel):
    strategy: Literal["none", "hook"] = "none"
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_hook_url(self) -> "ResetConfig":
        if self.strategy == "hook" and self.url is None:
            raise ValueError("sandbox.reset.url is required when sandbox.reset.strategy is 'hook'")
        return self


class SandboxConfig(BaseModel):
    mode: Literal["preview", "remote", "local_preview"] = "preview"
    reset: ResetConfig = Field(default_factory=ResetConfig)
    seed_state: str | None = None


class ProductConfig(BaseModel):
    name: str
    entry_url: HttpUrl
    description: str
    auth: AuthConfig = Field(default_factory=AuthConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)


class PersonaConfig(BaseModel):
    id: str
    name: str
    background: str
    goal: str
    behavior_style: str
    tech_level: Literal["low", "medium", "high"]


class PersonasFile(BaseModel):
    personas: list[PersonaConfig] = Field(min_length=1)


class JudgeCriterion(BaseModel):
    id: str
    question: str
    good: str
    bad: str


class SkillConfig(BaseModel):
    name: str
    version: str
    persona: str
    mission: str
    stop_conditions: list[str] = Field(min_length=1)
    judge_criteria: list[JudgeCriterion] = Field(min_length=1)


class ModelConfig(BaseModel):
    runtime_model: str = "unset"
    judge_model: str = "unset"
    persona_model: str = "unset"


class RuntimeProviderConfig(BaseModel):
    provider: Literal["auto", "openai-compatible", "openai", "anthropic", "google"] = "auto"
    api_key: str | None = None
    base_url: HttpUrl | None = None
    runtime_model: str = "unset"
    judge_model: str = "unset"
    persona_model: str = "unset"

    @model_validator(mode="after")
    def validate_provider_requirements(self) -> "RuntimeProviderConfig":
        if self.provider == "openai-compatible":
            if not self.api_key:
                raise ValueError("runtime provider api_key is required for openai-compatible")
            if self.base_url is None:
                raise ValueError("runtime provider base_url is required for openai-compatible")
        return self


class RunLimits(BaseModel):
    max_steps: int = 25
    max_runtime_seconds: int = 300


class RunSpec(BaseModel):
    product: ProductConfig
    persona: PersonaConfig
    skill: SkillConfig
    llm_config: ModelConfig = Field(default_factory=ModelConfig)
    runtime_provider: RuntimeProviderConfig = Field(default_factory=RuntimeProviderConfig)
    run_limits: RunLimits = Field(default_factory=RunLimits)
