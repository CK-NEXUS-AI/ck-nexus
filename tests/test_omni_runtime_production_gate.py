from pathlib import Path

import pytest

from creator_app.agnes.execution.result import ExecutionStatus
from creator_app.agnes_runtime import AgnesNervousSystem
from tests.omni_context_factory import make_test_omni_context

REPO = Path(__file__).resolve().parents[1]
SKILL_FILE = REPO / "creator_app" / "skills" / "agnes" / "SKILL.md"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "runtime_environment,request_environment",
    [("production", "development"), ("development", "production")],
)
async def test_production_request_never_uses_injected_test_context_factory(
    tmp_path, runtime_environment, request_environment
):
    calls = []

    def test_factory(request):
        calls.append(request.execution_id)
        return make_test_omni_context(request)

    agnes = AgnesNervousSystem(
        skill_file=SKILL_FILE,
        ledger_path=tmp_path / "ledger.jsonl",
        environment=runtime_environment,
        execution_context_factory=test_factory,
    )
    result = await agnes.execute_skill(
        {"id": "brain.plan", "execution_id": "production-gate-test"},
        goal="verify production authorization gate",
        correlation_id="corr-production-gate",
        environment=request_environment,
    )
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "omni_context_required"
    assert calls == []
