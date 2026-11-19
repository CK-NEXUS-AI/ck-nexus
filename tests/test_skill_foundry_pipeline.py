from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.skill_foundry import SkillDraftState, SkillFoundry
from creator_app.skill_foundry_pipeline import SkillFoundryPipeline
from idea_engine.engine import IdeaEngine
from idea_engine.graph import IdeaGraph
from idea_engine.knowledge_fabric import (
    CanonicalSourceKind,
    ClaimClass,
    KnowledgeClaim,
    SourceClass,
    SourceRecord,
    VerificationState,
)
from idea_engine.models import IdeaFeatures
from idea_engine.research_repository import (
    ResearchArtifactRecord,
    ResearchLineageEdgeRecord,
)


class FakeResearchRepository:
    def __init__(self, item: ResearchArtifactRecord):
        self.item = item

    async def load_artifact(self, *, tenant_id: str, artifact_id: str):
        if (tenant_id, artifact_id) != (self.item.tenant_id, self.item.artifact_id):
            raise KeyError("unknown research artifact for tenant")
        return self.item

    async def store_artifact(self, artifact):
        raise NotImplementedError


class FakeKnowledgeRepository:
    def __init__(self, sources, claims, revoked=frozenset()):
        self.sources = tuple(sources)
        self.claims = tuple(claims)
        self.revoked = frozenset(revoked)

    async def load_tenant(self, tenant_id: str):
        return (
            tuple(item for item in self.sources if item.tenant_id == tenant_id),
            tuple(item for item in self.claims if item.tenant_id == tenant_id),
            self.revoked,
        )

    async def store_source(self, source):
        raise NotImplementedError

    async def store_claim(self, claim):
        raise NotImplementedError

    async def set_source_revoked(self, **kwargs):
        raise NotImplementedError

    async def store_memory_proposal(self, proposal):
        raise NotImplementedError


def _fixture(tmp_path: Path, *, ready=True, revoked=False):
    tenant_id = "tenant-a"
    artifact_id = "research-a"
    source = SourceRecord(
        source_id="source-a",
        source_class=SourceClass.RESEARCH,
        locator="https://example.test/source-a",
        title="Authorized synthetic source",
        retrieved_at="2026-11-19T00:00:00Z",
        trust_score=0.8,
        tenant_id=tenant_id,
        source_kind=CanonicalSourceKind.PUBLIC_DOCUMENTATION,
        rights="user provided",
        source_hash="source-hash-a",
    )
    claim = KnowledgeClaim(
        claim_id="claim-a",
        subject="CK-NEXUS",
        predicate="capability",
        value="research-to-skill",
        claim_class=ClaimClass.FACT,
        source_ids=("source-a",),
        confidence=0.8,
        observed_at="2026-11-19T00:00:00Z",
        tenant_id=tenant_id,
        verification=VerificationState.MEASURED_NOT_VERIFIED,
    )
    artifact = ResearchArtifactRecord(
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        decision="READY_FOR_ANALYSIS" if ready else "CONTINUE_RESEARCH",
        truth_state="MEASURED_NOT_VERIFIED",
        ready_for_analysis=ready,
        scope={"topic": "CK-NEXUS Skill Foundry"},
        gaps=(),
        source_ids=("source-a",),
        claim_ids=("claim-a",),
        lineage_edges=(
            ResearchLineageEdgeRecord(
                edge_id="edge-a",
                from_node_kind="CLAIM",
                from_node_id="claim-a",
                to_node_kind="SOURCE",
                to_node_id="source-a",
                edge_type="DERIVED_FROM",
            ),
        ),
    )
    idea_engine = IdeaEngine(IdeaGraph(tmp_path / "ideas.json"))
    idea, _, _ = idea_engine.expand(
        title="Research to reusable skill",
        raw_input="Convert measured research into a governed, reusable skill proposal.",
        features=IdeaFeatures("architecture", evidence_availability=0.9),
        source_refs=[artifact_id],
    )
    ledger = AppendOnlyLedger(tmp_path / "evidence.jsonl")
    foundry = SkillFoundry(ledger)
    pipeline = SkillFoundryPipeline(
        idea_engine=idea_engine,
        research_repository=FakeResearchRepository(artifact),
        knowledge_repository=FakeKnowledgeRepository(
            [source], [claim], {"source-a"} if revoked else frozenset()
        ),
        foundry=foundry,
    )
    return pipeline, ledger, idea, artifact


def _create(pipeline, artifact, idea, permissions=None):
    return asyncio.run(
        pipeline.create_draft(
            tenant_id="tenant-a",
            research_artifact_id=artifact.artifact_id,
            idea_node_id=idea.id,
            owner="ck-nexus-research",
            source_permission_bases=(
                {"source-a": "user_provided"} if permissions is None else permissions
            ),
        )
    )


def test_pipeline_links_idea_research_knowledge_and_evidence(tmp_path: Path):
    pipeline, ledger, idea, artifact = _fixture(tmp_path)

    result = _create(pipeline, artifact, idea)

    assert result.draft.state is SkillDraftState.QUARANTINED
    assert result.draft.contract.source_lineage[0].source_id == "source-a"
    assert len(result.draft.evaluation_cases) == 4
    assert result.registration_event_hash
    assert result.lineage_event_hash
    assert ledger.verify().valid is True
    records = [json.loads(line) for line in ledger.path.read_text().splitlines()]
    assert [row["event_type"] for row in records] == [
        "skill_foundry.draft_registered",
        "skill_foundry.research_linked",
    ]
    linked = records[1]["payload"]
    assert linked["tenant_id"] == "tenant-a"
    assert linked["research_artifact_id"] == artifact.artifact_id
    assert linked["idea_node_id"] == idea.id
    assert linked["activation_allowed"] is False


def test_pipeline_rejects_research_not_ready_for_analysis(tmp_path: Path):
    pipeline, ledger, idea, artifact = _fixture(tmp_path, ready=False)

    with pytest.raises(ValueError, match="not READY_FOR_ANALYSIS"):
        _create(pipeline, artifact, idea)

    assert ledger.verify().entries == 0


def test_pipeline_rejects_revoked_sources(tmp_path: Path):
    pipeline, ledger, idea, artifact = _fixture(tmp_path, revoked=True)

    with pytest.raises(PermissionError, match="revoked sources"):
        _create(pipeline, artifact, idea)

    assert ledger.verify().entries == 0


def test_pipeline_requires_explicit_permission_for_each_source(tmp_path: Path):
    pipeline, ledger, idea, artifact = _fixture(tmp_path)

    with pytest.raises(ValueError, match="explicit permission basis"):
        _create(pipeline, artifact, idea, permissions={})

    assert ledger.verify().entries == 0


def test_pipeline_rejects_unknown_permission_basis(tmp_path: Path):
    pipeline, ledger, idea, artifact = _fixture(tmp_path)

    with pytest.raises(PermissionError, match="permission basis"):
        _create(pipeline, artifact, idea, permissions={"source-a": "unknown"})

    assert ledger.verify().entries == 0


def test_pipeline_rejects_idea_without_research_reference(tmp_path: Path):
    pipeline, ledger, idea, artifact = _fixture(tmp_path)
    pipeline._idea_engine.graph.update_node(idea.id, source_refs=[], actor="test")

    with pytest.raises(ValueError, match="must reference the research artifact"):
        _create(pipeline, artifact, idea)

    assert ledger.verify().entries == 0
