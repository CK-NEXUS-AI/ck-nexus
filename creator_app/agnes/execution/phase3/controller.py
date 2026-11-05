from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from creator_app.agnes_ledger import AppendOnlyLedger

from ..approval import StickyApprovalResolver
from ..request import SkillExecutionRequest
from ..result import ExecutionStatus
from .models import CandidateArtifact, PipelineHandle, PipelineState, PipelineStatus
from .workspace import ManagedWorkspace, WorkspaceLifecycleManager


class AutonomousDevController:
    """Bounded autonomous dev loop that always stops at CANDIDATE_READY."""

    def __init__(
        self,
        *,
        agnes,
        workspaces: WorkspaceLifecycleManager,
        ledger: AppendOnlyLedger,
        approvals: StickyApprovalResolver,
    ) -> None:
        self.agnes = agnes
        self.workspaces = workspaces
        self.ledger = ledger
        self.approvals = approvals
        self._pipelines: dict[str, PipelineStatus] = {}
        self._requests: dict[str, SkillExecutionRequest] = {}
        self._workspace_objs: dict[str, ManagedWorkspace] = {}
        self._results: dict[str, dict[str, dict]] = {}
        self._candidates: dict[str, CandidateArtifact] = {}

    async def start_pipeline(self, request: SkillExecutionRequest) -> PipelineHandle:
        pipeline_id = f"agnes_pipe_{uuid4().hex}"
        status = PipelineStatus(
            pipeline_id=pipeline_id,
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            state=PipelineState.PENDING_APPROVAL,
            baseline_commit=request.baseline_commit,
        )
        self._pipelines[pipeline_id] = status
        self._requests[pipeline_id] = request
        self._results[pipeline_id] = {}
        self._record(status, PipelineState.PENDING_APPROVAL, "pipeline_created")
        return PipelineHandle(pipeline_id, request.execution_id)

    async def advance(self, handle: PipelineHandle) -> PipelineState:
        status = self._require(handle.pipeline_id)
        request = self._requests[handle.pipeline_id]
        try:
            if status.state is PipelineState.PENDING_APPROVAL:
                skill = self.agnes.registry.get("hands.code_patch")
                risk = self.agnes.dispatcher.risk_classifier.classify(skill)
                fingerprint = self.agnes.approvals.fingerprint(request, risk)
                status.approval_fingerprint = fingerprint
                decision = self.agnes.dispatcher.policy.evaluate(
                    request, skill=skill, risk_class=risk
                )
                if not decision.allowed:
                    raise RuntimeError(decision.reason)
                if decision.requires_approval:
                    grant = None
                    if request.approval_id and self.agnes.approvals.is_approved(
                        approval_id=request.approval_id, fingerprint=fingerprint
                    ):
                        grant = request.approval_id
                    else:
                        match = self.agnes.approvals.find_matching(fingerprint)
                        grant = match.approval_id if match else None
                    if not grant:
                        status.error = "sticky_approval_required"
                        return status.state
                    if request.approval_id != grant:
                        request = replace(request, approval_id=grant)
                        self._requests[handle.pipeline_id] = request
                self._transition(status, PipelineState.APPROVED, "approval_verified")
                return status.state

            if status.state is PipelineState.APPROVED:
                ws = await self.workspaces.create(
                    request.baseline_commit or "", request.workspace_id or request.execution_id
                )
                self._workspace_objs[handle.pipeline_id] = ws
                status.workspace_id = ws.workspace_id
                self._transition(status, PipelineState.WORKSPACE_CREATED, "workspace_created")
                return status.state

            if status.state is PipelineState.WORKSPACE_CREATED:
                ws = self._workspace_objs[handle.pipeline_id]
                await self.workspaces.checkout(ws, request.baseline_commit or "")
                await self.workspaces.mark_running(ws)
                self._transition(status, PipelineState.BASELINE_CHECKED_OUT, "baseline_checked_out")
                return status.state

            if status.state is PipelineState.BASELINE_CHECKED_OUT:
                result = await self.agnes.execute_skill(
                    {
                        "id": "hands.code_patch",
                        "executor": "sandbox",
                        "inputs": request.inputs,
                        "allowlist_paths": list(request.allowlist_paths),
                        "granted_capabilities": list(request.granted_capabilities),
                        "execution_id": request.execution_id,
                    },
                    goal=request.goal,
                    correlation_id=request.correlation_id,
                    tenant_id=request.tenant_id,
                    actor_id=request.actor_id,
                    environment=request.environment,
                    workspace_id=status.workspace_id,
                    baseline_commit=request.baseline_commit,
                    approval_id=request.approval_id,
                    idempotency_key=request.idempotency_key,
                )
                self._results[handle.pipeline_id]["patch"] = result.as_dict()
                if result.status is not ExecutionStatus.SUCCEEDED:
                    raise RuntimeError(result.error or result.status.value)
                self._transition(status, PipelineState.CODE_PATCH_APPLIED, "patch_applied")
                return status.state

            if status.state is PipelineState.CODE_PATCH_APPLIED:
                result = await self.agnes.execute_skill(
                    {
                        "id": "hands.test",
                        "executor": "sandbox",
                        "inputs": {
                            "commands": [
                                list(
                                    request.inputs.get(
                                        "test_command", ["python", "-m", "compileall", "-q", "."]
                                    )
                                )
                            ]
                        },
                        "allowlist_paths": list(request.allowlist_paths),
                        "granted_capabilities": ["test", "shell"],
                        "execution_id": request.execution_id + "-test",
                    },
                    goal="validate candidate",
                    correlation_id=request.correlation_id,
                    tenant_id=request.tenant_id,
                    actor_id=request.actor_id,
                    environment=request.environment,
                    workspace_id=status.workspace_id,
                    baseline_commit=request.baseline_commit,
                    idempotency_key=(request.idempotency_key or request.execution_id) + ":test",
                )
                self._results[handle.pipeline_id]["test"] = result.as_dict()
                test_output = result.output if isinstance(result.output, dict) else {}
                command_results = test_output.get("commands")
                expected_command = list(
                    request.inputs.get(
                        "test_command", ["python", "-m", "compileall", "-q", "."]
                    )
                )
                if (
                    not isinstance(command_results, list)
                    or len(command_results) != 1
                    or command_results[0].get("argv") != expected_command
                ):
                    raise RuntimeError("test_execution_evidence_missing_or_mismatched")
                if result.status is not ExecutionStatus.SUCCEEDED:
                    raise RuntimeError(result.error or "tests_failed")
                if any(
                    item.get("returncode") != 0
                    or item.get("timed_out")
                    or item.get("output_limited")
                    for item in command_results
                ):
                    raise RuntimeError("tests_failed")
                self._transition(status, PipelineState.TESTS_EXECUTED, "tests_passed")
                return status.state

            if status.state is PipelineState.TESTS_EXECUTED:
                result = await self.agnes.execute_skill(
                    {
                        "id": "hands.security_scan",
                        "executor": "sandbox",
                        # The security scanner is policy-owned and uses its fixed
                        # secret-scan helper; never accept caller-supplied scan commands.
                        "inputs": {},
                        "allowlist_paths": list(request.allowlist_paths),
                        "granted_capabilities": ["security_scan", "shell"],
                        "execution_id": request.execution_id + "-scan",
                    },
                    goal="security scan candidate",
                    correlation_id=request.correlation_id,
                    tenant_id=request.tenant_id,
                    actor_id=request.actor_id,
                    environment=request.environment,
                    workspace_id=status.workspace_id,
                    baseline_commit=request.baseline_commit,
                    idempotency_key=(request.idempotency_key or request.execution_id) + ":scan",
                )
                self._results[handle.pipeline_id]["scan"] = result.as_dict()
                if result.status is not ExecutionStatus.SUCCEEDED:
                    raise RuntimeError(result.error or "security_scan_failed")
                self._transition(status, PipelineState.SECURITY_SCANNED, "security_scan_passed")
                return status.state

            if status.state is PipelineState.SECURITY_SCANNED:
                diff = await self.workspaces.get_diff(self._workspace_objs[handle.pipeline_id])
                self._results[handle.pipeline_id]["diff"] = {"unified_diff": diff}
                self._transition(status, PipelineState.DIFF_REVIEWED, "diff_collected")
                return status.state

            if status.state is PipelineState.DIFF_REVIEWED:
                ref = self.ledger.append(
                    "agnes_pipeline_evidence",
                    {
                        "pipeline_id": status.pipeline_id,
                        "execution_id": status.execution_id,
                        "correlation_id": status.correlation_id,
                        "baseline_commit": status.baseline_commit,
                        "results": self._results[handle.pipeline_id],
                    },
                )
                self._results[handle.pipeline_id]["evidence_ref"] = {"hash": ref["hash"]}
                self._transition(status, PipelineState.EVIDENCE_COLLECTED, "evidence_collected")
                return status.state

            if status.state is PipelineState.EVIDENCE_COLLECTED:
                candidate = CandidateArtifact(
                    candidate_id=f"candidate_{uuid4().hex}",
                    execution_id=status.execution_id,
                    pipeline_id=status.pipeline_id,
                    baseline_commit=status.baseline_commit or "",
                    result_commit=None,
                    diff=self._results[handle.pipeline_id]["diff"]["unified_diff"],
                    test_result=self._results[handle.pipeline_id]["test"],
                    security_scan=self._results[handle.pipeline_id]["scan"],
                    evidence_refs=(self._results[handle.pipeline_id]["evidence_ref"]["hash"],),
                    status="candidate",
                    created_at=datetime.now(UTC).isoformat(),
                    requires_merge_approval=True,
                )
                self._candidates[handle.pipeline_id] = candidate
                await self.workspaces.mark_candidate(self._workspace_objs[handle.pipeline_id])
                self._transition(
                    status, PipelineState.CANDIDATE_READY, "candidate_ready_stop_before_merge"
                )
                return status.state

            return status.state
        except Exception as exc:
            status.error = str(exc)
            await self._rollback(handle.pipeline_id, str(exc))
            return self._pipelines[handle.pipeline_id].state

    async def run_to_candidate(
        self, handle: PipelineHandle, *, max_steps: int = 16
    ) -> PipelineStatus:
        for _ in range(max_steps):
            state = await self.advance(handle)
            if state in {
                PipelineState.CANDIDATE_READY,
                PipelineState.DISCARDED,
                PipelineState.ROLLED_BACK,
                PipelineState.FAILED,
            }:
                break
            if (
                state is PipelineState.PENDING_APPROVAL
                and self._pipelines[handle.pipeline_id].error
            ):
                break
        return self._require(handle.pipeline_id)

    async def get_status(self, pipeline_id: str) -> PipelineStatus:
        return self._require(pipeline_id)

    async def discard(self, pipeline_id: str, reason: str) -> None:
        status = self._require(pipeline_id)
        ws = self._workspace_objs.get(pipeline_id)
        if ws is not None:
            await self.workspaces.discard(ws)
        status.error = reason
        self._transition(status, PipelineState.DISCARDED, reason)

    async def collect_candidate(self, pipeline_id: str) -> CandidateArtifact:
        status = self._require(pipeline_id)
        if status.state is not PipelineState.CANDIDATE_READY:
            raise RuntimeError("candidate_not_ready")
        return self._candidates[pipeline_id]

    async def _rollback(self, pipeline_id: str, reason: str) -> None:
        status = self._require(pipeline_id)
        ws = self._workspace_objs.get(pipeline_id)
        if ws is not None:
            await self.workspaces.discard(ws)
        self._transition(status, PipelineState.ROLLED_BACK, f"rollback:{reason}")

    def _record(self, status: PipelineStatus, state: PipelineState, event: str) -> None:
        ts = datetime.now(UTC).isoformat()
        row = {
            "state": state.value,
            "event": event,
            "timestamp": ts,
            "correlation_id": status.correlation_id,
            "execution_id": status.execution_id,
        }
        status.history.append(row)
        self.ledger.append("agnes_pipeline_state", {"pipeline_id": status.pipeline_id, **row})

    def _transition(self, status: PipelineStatus, state: PipelineState, event: str) -> None:
        status.state = state
        status.error = (
            None
            if state
            not in {PipelineState.DISCARDED, PipelineState.ROLLED_BACK, PipelineState.FAILED}
            else status.error
        )
        self._record(status, state, event)

    def _require(self, pipeline_id: str) -> PipelineStatus:
        try:
            return self._pipelines[pipeline_id]
        except KeyError as exc:
            raise KeyError("pipeline_not_found") from exc
