from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from doppel.config.models import RunSpec


@dataclass(slots=True)
class AuthContext:
    required: bool
    username: str | None
    password: str | None


@dataclass(slots=True)
class ResetResult:
    executed: bool
    strategy: str
    detail: str


@dataclass(slots=True)
class SandboxContext:
    run_id: str
    mode: str
    entry_url: str
    artifact_dir: Path
    auth_context: AuthContext
    seed_state: str | None
    reset_strategy: str
    reset_url: str | None
    browser_context: object | None = None


class SandboxManager(ABC):
    def __init__(self, artifact_root: Path | None = None) -> None:
        default_root = (Path.cwd() / ".doppel" / "runs").resolve()
        self.artifact_root = artifact_root.resolve() if artifact_root is not None else default_root

    @abstractmethod
    def prepare(self, spec: RunSpec) -> SandboxContext:
        """Prepare a sandbox context for a run."""

    @abstractmethod
    def reset(self, ctx: SandboxContext) -> ResetResult:
        """Reset the sandbox before a run."""

    @abstractmethod
    def teardown(self, ctx: SandboxContext) -> None:
        """Tear down sandbox resources."""

    def _new_run_dir(self, spec: RunSpec) -> tuple[str, Path]:
        run_id = uuid4().hex[:12]
        page_slug = self._artifact_slug(spec)
        persona_slug = self._slugify(spec.persona.id or spec.persona.name)
        artifact_dir = self._unique_artifact_dir(f"{page_slug}-{persona_slug}")
        artifact_dir.mkdir(parents=True, exist_ok=False)
        return run_id, artifact_dir

    def _unique_artifact_dir(self, base_name: str) -> Path:
        artifact_dir = self.artifact_root / base_name
        if not artifact_dir.exists():
            return artifact_dir
        for index in range(2, 1000):
            candidate = self.artifact_root / f"{base_name}-{index}"
            if not candidate.exists():
                return candidate
        raise RuntimeError(f"无法创建唯一输出目录：{base_name}")

    @staticmethod
    def _artifact_slug(spec: RunSpec) -> str:
        source = spec.product.name.strip()
        if not source:
            source = urlparse(str(spec.product.entry_url)).netloc
        return SandboxManager._slugify(source) or "page"

    @staticmethod
    def _slugify(source: str) -> str:
        return re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]+", "-", source.lower()).strip("-")

    @staticmethod
    def _build_auth_context(spec: RunSpec) -> AuthContext:
        return AuthContext(
            required=spec.product.auth.required,
            username=spec.product.auth.username,
            password=spec.product.auth.password,
        )

    @staticmethod
    def _build_reset_context(spec: RunSpec) -> tuple[str, str | None]:
        return spec.product.sandbox.reset.strategy, (
            str(spec.product.sandbox.reset.url) if spec.product.sandbox.reset.url else None
        )

    @staticmethod
    def _execute_reset_hook(ctx: SandboxContext) -> ResetResult:
        if ctx.reset_strategy != "hook" or ctx.reset_url is None:
            return ResetResult(executed=False, strategy="none", detail="未配置 reset hook")
        try:
            response = httpx.post(ctx.reset_url, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return ResetResult(executed=False, strategy="hook", detail=f"reset hook 执行失败：{exc}")
        return ResetResult(executed=True, strategy="hook", detail=f"reset hook 返回状态码 {response.status_code}")
