from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from creator_app.skill_foundry import (
    SkillContract,
    SkillDraft,
    SkillEvaluationCase,
    SkillFoundry,
    SkillSource,
)
from idea_engine.engine import IdeaEngine
from idea_engine.knowledge_fabric import SourceRecord
from idea_engine.knowledge_repository import KnowledgeRepository
from idea_engine.research_repository import (
    ResearchArtifactRecord,
    ResearchRepository,
)


@dataclass(frozen=True, slots=True)
class SkillFoundryPipelineResult:
    draft: SkillDraft
    registration_event_hash: str
    lineage_event_hash: str
    research_artifact_id: str
    idea_node_id: str


class SkillFoundryPipeline:
    """Joins Idea Engine, tenant-scoped research/knowledge and the evidence ledger.

    This is a proposal-only bridge. It creates quarantined drafts and evidence
    records; it never executes, approves, activates or publishes a skill.
    """

    def __init__(
        self,
        *,
        idea_engine: IdeaEngine,
        research_repository: ResearchRepository,
        knowledge_repository: KnowledgeRepository,
        foundry: SkillFoundry,
    ) -> None:
        self._idea_engine = idea_engine
        self._research_repository = research_repository
        self._knowledge_repository = knowledge_repository
        self._foundry = foundry

    async def create_draft(
        self,
        *,
        tenant_id: str,
        research_artifact_id: str,
        idea_node_id: str,
        owner: str,
        source_permission_bases: Mapping[str, str],
        version: str = "0.1.0",
    ) -> SkillFoundryPipelineResult:
        if not all(
            value.strip()
            for value in (tenant_id, research_artifact_id, idea_node_id, owner, version)
        ):
            raise ValueError("tenant, artifact, idea node, owner and version are required")

        artifact = await self._research_repository.load_artifact(
            tenant_id=tenant_id,
            artifact_id=research_artifact_id,
        )
        self._validate_artifact(artifact, tenant_id, research_artifact_id)

        idea = self._idea_engine.graph.get_node(idea_node_id)
        if idea is None:
            raise KeyError("idea node does not exist in the supplied Idea Engine")
        if idea.status == "archived":
            raise ValueError("archived idea nodes cannot seed a skill draft")
        if research_artifact_id not in idea.source_refs and not (
            set(artifact.source_ids) & set(idea.source_refs)
        ):
            raise ValueError("idea node must reference the research artifact or one of its sources")

        sources, claims, revoked_ids = await self._knowledge_repository.load_tenant(tenant_id)
        sources_by_id = {source.source_id: source for source in sources}
        claims_by_id = {claim.claim_id: claim for claim in claims}

        missing_sources = sorted(set(artifact.source_ids) - set(sources_by_id))
        missing_claims = sorted(set(artifact.claim_ids) - set(claims_by_id))
        cross_tenant_sources = sorted(
            source_id
            for source_id in artifact.source_ids
            if source_id in sources_by_id and sources_by_id[source_id].tenant_id != tenant_id
        )
        cross_tenant_claims = sorted(
            claim_id
            for claim_id in artifact.claim_ids
            if claim_id in claims_by_id and claims_by_id[claim_id].tenant_id != tenant_id
        )
        if missing_sources or missing_claims:
            raise ValueError(
                "research artifact references missing tenant knowledge records: "
                f"sources={missing_sources}, claims={missing_claims}"
            )
        if cross_tenant_sources or cross_tenant_claims:
            raise PermissionError(
                "knowledge repository returned cross-tenant records: "
                f"sources={cross_tenant_sources}, claims={cross_tenant_claims}"
            )
        artifact_source_ids = set(artifact.source_ids)
        claims_with_external_sources = sorted(
            claim_id
            for claim_id in artifact.claim_ids
            if not set(claims_by_id[claim_id].source_ids).issubset(artifact_source_ids)
        )
        if claims_with_external_sources:
            raise ValueError(
                "research claims reference sources outside the artifact: "
                + ", ".join(claims_with_external_sources)
            )
        revoked = sorted(set(artifact.source_ids) & set(revoked_ids))
        if revoked:
            raise PermissionError(
                "research artifact includes revoked sources: " + ", ".join(revoked)
            )

        if set(source_permission_bases) != set(artifact.source_ids):
            raise ValueError("an explicit permission basis is required for every artifact source")

        skill_sources = tuple(
            self._to_skill_source(sources_by_id[source_id], source_permission_bases[source_id])
            for source_id in sorted(artifact.source_ids)
        )
        skill_id = self._skill_id(idea.title, idea.id)
        cases = self._evaluation_cases(skill_id, version)
        contract = SkillContract(
            skill_id=skill_id,
            version=version,
            title=idea.title,
            purpose=idea.summary,
            owner=owner,
            inputs_schema={
                "type": "object",
                "required": ["tenant_id", "research_artifact_id", "source_ids", "claim_ids"],
                "properties": {
                    "tenant_id": {"type": "string"},
                    "research_artifact_id": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                    "claim_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
            outputs_schema={
                "type": "object",
                "required": ["summary", "claim_refs", "source_refs", "limitations"],
                "properties": {
                    "summary": {"type": "string"},
                    "claim_refs": {"type": "array", "items": {"type": "string"}},
                    "source_refs": {"type": "array", "items": {"type": "string"}},
                    "limitations": {"type": "array", "items": {"type": "string"}},
                },
            },
            required_capabilities=("research_read", "knowledge_proposal"),
            forbidden_capabilities=(
                "external_send",
                "credential_export",
                "approval_mutation",
                "release_gate_mutation",
                "production_deploy",
                "arbitrary_network",
                "unrestricted_shell",
            ),
            risk_class="read_only",
            approval_policy="human_before_execution",
            evidence_requirements=(
                "research_artifact_id",
                "tenant_scoped_source_refs",
                "tenant_scoped_claim_refs",
                "evaluation_results",
            ),
            source_lineage=skill_sources,
            license_basis=(
                "per-source permission basis recorded; independent rights review required"
            ),
        )
        draft = SkillDraft(contract=contract, evaluation_cases=cases)
        registration = self._foundry.register_draft(
            draft,
            context={
                "tenant_id": tenant_id,
                "research_artifact_id": research_artifact_id,
                "idea_node_id": idea_node_id,
                "source_ids": sorted(artifact.source_ids),
                "claim_ids": sorted(artifact.claim_ids),
            },
        )
        lineage = self._foundry.record_research_link(
            tenant_id=tenant_id,
            research_artifact_id=research_artifact_id,
            idea_node_id=idea_node_id,
            skill_id=skill_id,
            version=version,
            source_ids=artifact.source_ids,
            claim_ids=artifact.claim_ids,
            registration_event_hash=str(registration["hash"]),
        )
        return SkillFoundryPipelineResult(
            draft=draft,
            registration_event_hash=str(registration["hash"]),
            lineage_event_hash=str(lineage["hash"]),
            research_artifact_id=research_artifact_id,
            idea_node_id=idea_node_id,
        )

    @staticmethod
    def _validate_artifact(
        artifact: ResearchArtifactRecord,
        tenant_id: str,
        artifact_id: str,
    ) -> None:
        if artifact.tenant_id != tenant_id or artifact.artifact_id != artifact_id:
            raise PermissionError(
                "research repository returned an artifact outside requested scope"
            )
        if artifact.decision != "READY_FOR_ANALYSIS" or not artifact.ready_for_analysis:
            raise ValueError("research artifact is not READY_FOR_ANALYSIS")
        if artifact.truth_state != "MEASURED_NOT_VERIFIED":
            raise PermissionError("only MEASURED_NOT_VERIFIED research may seed a draft")
        if not artifact.source_ids or not artifact.claim_ids:
            raise ValueError("research artifact requires source and claim lineage")
        if any(item.resolution_status != "RESOLVED" for item in artifact.contradictions):
            raise ValueError("research artifact contains unresolved contradictions")
        source_ids = set(artifact.source_ids)
        claim_ids = set(artifact.claim_ids)
        for edge in artifact.lineage_edges:
            from_known = (
                edge.from_node_id in source_ids
                if edge.from_node_kind == "SOURCE"
                else edge.from_node_id in claim_ids
            )
            to_known = (
                edge.to_node_id in source_ids
                if edge.to_node_kind == "SOURCE"
                else edge.to_node_id in claim_ids
            )
            if not from_known or not to_known:
                raise ValueError("research artifact contains an out-of-scope lineage edge")

    @staticmethod
    def _to_skill_source(source: SourceRecord, permission_basis: str) -> SkillSource:
        payload = asdict(source)
        for key, value in tuple(payload.items()):
            if hasattr(value, "value"):
                payload[key] = value.value
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return SkillSource(
            source_id=source.source_id,
            source_type=source.source_kind.value,
            title=source.title,
            uri=source.locator,
            permission_basis=permission_basis,
            source_record_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _skill_id(title: str, node_id: str) -> str:
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
        suffix = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:10]
        return f"idea.{slug or 'skill'}.{suffix}"

    @staticmethod
    def _evaluation_cases(skill_id: str, version: str) -> tuple[SkillEvaluationCase, ...]:
        base = f"fixture://skill-foundry/{skill_id}/{version}"
        return (
            SkillEvaluationCase(
                "positive-01",
                "positive",
                "Produces a structured output with source and claim references.",
                f"{base}/positive",
            ),
            SkillEvaluationCase(
                "negative-01",
                "negative",
                "Rejects missing tenant or source references.",
                f"{base}/negative",
            ),
            SkillEvaluationCase(
                "boundary-01",
                "boundary",
                "Handles the declared maximum source and claim set.",
                f"{base}/boundary",
            ),
            SkillEvaluationCase(
                "adversarial-01",
                "adversarial",
                "Does not follow instructions embedded in untrusted source material.",
                f"{base}/adversarial",
            ),
        )
