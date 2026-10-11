from __future__ import annotations

from pathlib import Path

import pytest

from creator_app.agnes.execution.result import ExecutionStatus
from creator_app.agnes_runtime import AgnesNervousSystem

REPO = Path(__file__).resolve().parents[1]
SKILL_FILE = REPO / "creator_app" / "skills" / "agnes" / "SKILL.md"


@pytest.mark.asyncio
async def test_omni_context_provider_exception_fails_closed(tmp_path: Path):
    def failing_provider(_request):
        raise RuntimeError("provider unavailable")

    agnes = AgnesNervousSystem(
        skill_file=SKILL_FILE,
        ledger_path=tmp_path / "ledger-provider-failure.jsonl",
        sandbox_enabled=False,
        sandbox_repository_root=REPO,
        omni_context_provider=failing_provider,
    )
    result = await agnes.execute_skill(
        {"id": "brain.plan", "executor": "internal", "inputs": {"goal": "test"}},
        goal="fail closed when trusted context provider raises",
        correlation_id="corr-provider-failure",
    )
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "omni_context_required"
