from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from creator_app.catalog import get_agent_spec
from creator_app.config import Settings
from creator_app.runtime import CreatorRuntime
from creator_app.schemas import RunRequest, RunResult
from creator_app.storage import RunStore


class CreatorService:
    def __init__(
        self,
        settings: Settings,
        runtime: CreatorRuntime,
        store: RunStore,
    ) -> None:
        self.settings = settings
        self.runtime = runtime
        self.store = store

    async def create_run(self, request: RunRequest) -> RunResult:
        spec = get_agent_spec(request.agent_id)
        started = perf_counter()
        selection = await self.runtime.run(spec, request)
        duration_ms = max(1, round((perf_counter() - started) * 1_000))

        run = RunResult(
            id=f"run_{uuid4().hex}",
            session_id=request.session_id,
            agent_id=spec.id,
            agent_name=spec.name,
            prompt=request.prompt,
            audience=request.audience,
            platform=request.platform,
            tone=request.tone,
            language=request.language,
            content=selection.content,
            model=selection.model,
            mode=selection.mode,
            status="completed",
            duration_ms=duration_ms,
            created_at=datetime.now(UTC),
        )
        self.store.save(run)
        return run
