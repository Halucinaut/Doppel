from __future__ import annotations

from doppel.config.models import RunSpec
from doppel.sandbox.base import ResetResult, SandboxContext, SandboxManager


class RemoteUrlSandbox(SandboxManager):
    def prepare(self, spec: RunSpec) -> SandboxContext:
        run_id, artifact_dir = self._new_run_dir()
        reset_strategy, reset_url = self._build_reset_context(spec)
        return SandboxContext(
            run_id=run_id,
            mode="remote",
            entry_url=str(spec.product.entry_url),
            artifact_dir=artifact_dir,
            auth_context=self._build_auth_context(spec),
            seed_state=spec.product.sandbox.seed_state,
            reset_strategy=reset_strategy,
            reset_url=reset_url,
        )

    def reset(self, ctx: SandboxContext) -> ResetResult:
        return self._execute_reset_hook(ctx)

    def teardown(self, ctx: SandboxContext) -> None:
        return None
