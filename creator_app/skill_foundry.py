from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from creator_app.agnes.execution.evidence import redact
from creator_app.agnes_ledger import AppendOnlyLedger

_SKILL_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_ALLOWED_PERMISSION_BASES = frozenset(
    {"user_provided", "public_authorized", "official_documentation", "internal_authorized"}
)
_REQUIRED_TEST_KINDS = frozenset({"positive", "negative", "boundary", "adversarial"})
_FORBIDDEN_CAPABILITIES = frozenset(
    {
        "credential_export",
        "approval_mutation",
        "release_gate_mutation",
        "unrestricted_shell",
        "arbitrary_network",
        "production_deploy",
    }
)


class SkillDraftState(StrEnum):
    QUARANTINED = "QUARANTINED"
    EVALUATED = "EVALUATED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class SkillSource:
    source_id: str
    source_type: str
    title: str
    uri: str
    permission_basis: str
    source_record_sha256: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.source_id,
                self.source_type,
                self.title,
                self.permission_basis,
            )
        ):
            raise ValueError("source identity, type, title and permission basis are required")
        if self.uri and not self.uri.startswith(("https://", "http://", "urn:")):
            raise ValueError("source uri must use https, http or urn")
        if self.permission_basis not in _ALLOWED_PERMISSION_BASES:
            raise PermissionError("source permission basis is not an approved category")
        if not _SHA256.fullmatch(self.source_record_sha256):
            raise ValueError("source_record_sha256 must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class SkillEvaluationCase:
    case_id: str
    kind: str
    objective: str
    synthetic_fixture_ref: str

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.objective.strip():
            raise ValueError("evaluation case id and objective are required")
        if self.kind not in _REQUIRED_TEST_KINDS:
            raise ValueError("unsupported evaluation case kind")
        if not self.synthetic_fixture_ref.startswith("fixture://"):
            raise ValueError("evaluation cases must reference synthetic fixture:// data")


@dataclass(frozen=True, slots=True)
class SkillContract:
    skill_id: str
    version: str
    title: str
    purpose: str
    owner: str
    inputs_schema: dict[str, Any]
    outputs_schema: dict[str, Any]
    required_capabilities: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]
    risk_class: str
    approval_policy: str
    evidence_requirements: tuple[str, ...]
    source_lineage: tuple[SkillSource, ...]
    license_basis: str
    rollback_version: str | None = None

    def __post_init__(self) -> None:
        if not _SKILL_ID.fullmatch(self.skill_id):
            raise ValueError("skill_id must be a lowercase stable identifier")
        if not _SEMVER.fullmatch(self.version):
            raise ValueError("skill version must use semantic versioning")
        if self.rollback_version is not None and not _SEMVER.fullmatch(self.rollback_version):
            raise ValueError("rollback_version must use semantic versioning")
        if not all(
            value.strip() for value in (self.title, self.purpose, self.owner, self.license_basis)
        ):
            raise ValueError("title, purpose, owner and license_basis are required")
        if not self.inputs_schema or not self.outputs_schema:
            raise ValueError("input and output schemas are required")
        if (
            self.inputs_schema.get("type") != "object"
            or self.outputs_schema.get("type") != "object"
        ):
            raise ValueError("skill input and output schemas must be objects")
        if not self.required_capabilities:
            raise ValueError("at least one required capability must be declared")
        if set(self.required_capabilities) & set(self.forbidden_capabilities):
            raise ValueError("a capability cannot be both required and forbidden")
        if set(self.required_capabilities) & _FORBIDDEN_CAPABILITIES:
            raise PermissionError("skill contract requests a globally forbidden capability")
        if self.risk_class not in {"read_only", "local_write", "external_write", "high_impact"}:
            raise ValueError("unsupported skill risk class")
        if self.approval_policy not in {
            "none",
            "human_before_execution",
            "human_before_external_effect",
        }:
            raise ValueError("unsupported approval policy")
        if self.risk_class in {"external_write", "high_impact"} and self.approval_policy == "none":
            raise PermissionError("external/high-impact skills require human approval")
        if not self.evidence_requirements:
            raise ValueError("at least one evidence requirement is required")
        if not self.source_lineage:
            raise ValueError("at least one permission-scoped source is required")


@dataclass(frozen=True, slots=True)
class SkillDraft:
    contract: SkillContract
    evaluation_cases: tuple[SkillEvaluationCase, ...]
    state: SkillDraftState = SkillDraftState.QUARANTINED

    def __post_init__(self) -> None:
        case_ids = [case.case_id for case in self.evaluation_cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation case ids must be unique")
        kinds = {case.kind for case in self.evaluation_cases}
        missing = _REQUIRED_TEST_KINDS - kinds
        if missing:
            raise ValueError("missing evaluation kinds: " + ", ".join(sorted(missing)))
        if len(self.evaluation_cases) < 4:
            raise ValueError("at least four evaluation cases are required")
        if self.state is not SkillDraftState.QUARANTINED:
            raise ValueError("new skill drafts must start in quarantine")


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    case_id: str
    passed: bool
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.evidence_ref.strip():
            raise ValueError("evaluation result requires case id and evidence reference")


class SkillFoundry:
    """Creates auditable skill proposals. It never executes, activates or publishes skills."""

    def __init__(self, ledger: AppendOnlyLedger) -> None:
        self._ledger = ledger

    @staticmethod
    def _canonical_hash(value: object) -> str:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _find_registered_draft(self, *, skill_id: str, version: str) -> dict[str, Any] | None:
        integrity = self._ledger.verify()
        if not integrity.valid:
            raise RuntimeError("skill foundry ledger integrity check failed")
        if not self._ledger.path.exists():
            return None
        with self._ledger.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                payload = record.get("payload", {})
                contract = payload.get("contract", {})
                if (
                    record.get("event_type") == "skill_foundry.draft_registered"
                    and contract.get("skill_id") == skill_id
                    and contract.get("version") == version
                ):
                    return payload
        return None

    def register_draft(
        self, draft: SkillDraft, *, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = redact(asdict(draft))
        if context is not None:
            allowed_context = {
                "tenant_id",
                "research_artifact_id",
                "idea_node_id",
                "source_ids",
                "claim_ids",
            }
            if set(context) != allowed_context:
                raise ValueError("registration context must contain the complete lineage scope")
            if not all(
                isinstance(context[key], str) and context[key].strip()
                for key in ("tenant_id", "research_artifact_id", "idea_node_id")
            ):
                raise ValueError("registration context identity fields are required")
            for key in ("source_ids", "claim_ids"):
                values = context[key]
                if (
                    not isinstance(values, (list, tuple))
                    or not values
                    or any(not isinstance(value, str) or not value.strip() for value in values)
                    or len(values) != len(set(values))
                ):
                    raise ValueError("registration context requires unique source and claim IDs")
            payload["registration_context"] = redact(context)
        payload["state"] = SkillDraftState.QUARANTINED.value
        payload["draft_sha256"] = self._canonical_hash(payload)
        return self._ledger.append("skill_foundry.draft_registered", payload)

    def record_evaluation(
        self,
        *,
        skill_id: str,
        version: str,
        cases: tuple[SkillEvaluationCase, ...],
        results: tuple[EvaluationResult, ...],
    ) -> dict[str, Any]:
        if len(cases) < 4 or {case.kind for case in cases} != _REQUIRED_TEST_KINDS:
            raise ValueError(
                "evaluation must cover positive, negative, boundary and adversarial cases"
            )
        if not _SKILL_ID.fullmatch(skill_id) or not _SEMVER.fullmatch(version):
            raise ValueError("evaluation requires a valid skill id and semantic version")
        expected = {case.case_id for case in cases}
        actual = {result.case_id for result in results}
        if len(expected) != len(cases) or expected != actual or len(actual) != len(results):
            raise ValueError("evaluation results must cover every case exactly once")
        by_id = {result.case_id: result for result in results}
        missing_evidence = [
            case_id
            for case_id, result in by_id.items()
            if not _SHA256.fullmatch(result.evidence_ref)
        ]
        if missing_evidence:
            raise ValueError("every evaluation result requires a SHA-256 evidence reference")
        registered = self._find_registered_draft(skill_id=skill_id, version=version)
        if registered is None:
            raise ValueError("evaluation requires a matching registered skill draft")
        registered_cases = registered.get("evaluation_cases", [])
        supplied_cases = [asdict(case) for case in cases]
        if sorted(registered_cases, key=lambda item: item["case_id"]) != sorted(
            supplied_cases, key=lambda item: item["case_id"]
        ):
            raise ValueError("evaluation cases must match the registered draft exactly")
        passed = all(result.passed for result in results)
        payload = {
            "skill_id": skill_id,
            "version": version,
            "case_count": len(cases),
            "passed_count": sum(result.passed for result in results),
            "failed_case_ids": sorted(result.case_id for result in results if not result.passed),
            "results": [
                asdict(result) for result in sorted(results, key=lambda item: item.case_id)
            ],
            "state": (
                SkillDraftState.EVALUATED.value if passed else SkillDraftState.QUARANTINED.value
            ),
            "promotion_allowed": False,
        }
        payload["evaluation_sha256"] = self._canonical_hash(payload)
        return self._ledger.append("skill_foundry.evaluation_recorded", redact(payload))

    def record_research_link(
        self,
        *,
        tenant_id: str,
        research_artifact_id: str,
        idea_node_id: str,
        skill_id: str,
        version: str,
        source_ids: tuple[str, ...],
        claim_ids: tuple[str, ...],
        registration_event_hash: str,
    ) -> dict[str, Any]:
        if not all(
            value.strip()
            for value in (
                tenant_id,
                research_artifact_id,
                idea_node_id,
                skill_id,
                version,
                registration_event_hash,
            )
        ):
            raise ValueError(
                "tenant, research, idea, skill and registration references are required"
            )
        if (
            not _SEMVER.fullmatch(version)
            or not _SHA256.fullmatch(registration_event_hash)
            or not source_ids
            or not claim_ids
            or any(not item.strip() for item in (*source_ids, *claim_ids))
            or len(source_ids) != len(set(source_ids))
            or len(claim_ids) != len(set(claim_ids))
        ):
            raise ValueError(
                "research link requires version, registration hash, sources and claims"
            )
        integrity = self._ledger.verify()
        if not integrity.valid:
            raise RuntimeError("skill foundry ledger integrity check failed")
        registration_found = False
        if self._ledger.path.exists():
            with self._ledger.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    payload = record.get("payload", {})
                    if (
                        record.get("hash") == registration_event_hash
                        and record.get("event_type") == "skill_foundry.draft_registered"
                        and payload.get("contract", {}).get("skill_id") == skill_id
                        and payload.get("contract", {}).get("version") == version
                        and payload.get("registration_context", {})
                        == {
                            "tenant_id": tenant_id,
                            "research_artifact_id": research_artifact_id,
                            "idea_node_id": idea_node_id,
                            "source_ids": sorted(set(source_ids)),
                            "claim_ids": sorted(set(claim_ids)),
                        }
                        and sorted(
                            item["source_id"]
                            for item in payload.get("contract", {}).get("source_lineage", [])
                        )
                        == sorted(set(source_ids))
                    ):
                        registration_found = True
                        break
        if not registration_found:
            raise ValueError("research link must reference a matching registered draft")
        payload = {
            "tenant_id": tenant_id,
            "research_artifact_id": research_artifact_id,
            "idea_node_id": idea_node_id,
            "skill_id": skill_id,
            "version": version,
            "source_ids": sorted(set(source_ids)),
            "claim_ids": sorted(set(claim_ids)),
            "registration_event_hash": registration_event_hash,
            "activation_allowed": False,
        }
        payload["lineage_sha256"] = self._canonical_hash(payload)
        return self._ledger.append("skill_foundry.research_linked", redact(payload))

    def _has_matching_evaluation(self, *, skill_id: str, version: str, evaluation_ref: str) -> bool:
        integrity = self._ledger.verify()
        if not integrity.valid:
            raise RuntimeError("skill foundry ledger integrity check failed")
        if not self._ledger.path.exists():
            return False
        with self._ledger.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                payload = record.get("payload", {})
                if (
                    record.get("hash") == evaluation_ref
                    and record.get("event_type") == "skill_foundry.evaluation_recorded"
                    and payload.get("skill_id") == skill_id
                    and payload.get("version") == version
                    and payload.get("state") == SkillDraftState.EVALUATED.value
                ):
                    return True
        return False

    def request_human_review(
        self,
        *,
        skill_id: str,
        version: str,
        evaluation_ref: str,
        reviewer_role: str = "independent_reviewer",
    ) -> dict[str, Any]:
        if not all(value.strip() for value in (skill_id, version, evaluation_ref, reviewer_role)):
            raise ValueError("skill, version, evaluation reference and reviewer role are required")
        if not _SEMVER.fullmatch(version) or not _SHA256.fullmatch(evaluation_ref):
            raise ValueError(
                "review requires a semantic version and SHA-256 evaluation event reference"
            )
        if not self._has_matching_evaluation(
            skill_id=skill_id, version=version, evaluation_ref=evaluation_ref
        ):
            raise ValueError("review must reference a matching passed evaluation event")
        return self._ledger.append(
            "skill_foundry.human_review_requested",
            {
                "skill_id": skill_id,
                "version": version,
                "evaluation_ref": evaluation_ref,
                "reviewer_role": reviewer_role,
                "state": SkillDraftState.HUMAN_REVIEW_REQUIRED.value,
                "activation_allowed": False,
                "reason": "human approval and runtime integration are separate gated steps",
            },
        )
