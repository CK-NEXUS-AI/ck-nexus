import hashlib
import json

from creator_app.council_authority import omni_evidence
from creator_app.council_authority.omni_evidence import CouncilStoreEvidenceVerifier, verify
from creator_app.council_authority.storage import AuthorityStore
from tests.test_omni_issuer import request
from tests.test_omni_provider import context


def test_council_evidence_verifier_requires_task_bound_verified_refs(tmp_path, monkeypatch):
    store = AuthorityStore(str(tmp_path / "council.sqlite"))
    req = request()
    req = type(req)(
        execution_id=req.execution_id,
        correlation_id=req.correlation_id,
        skill_id=req.skill_id,
        skill_version=req.skill_version,
        executor=req.executor,
        goal=req.goal,
        plan_step=req.plan_step,
        inputs={
            "evidence_refs": ["commit-ref"],
            "evidence_task_id": "workspace-1",
        },
        workspace_id="workspace-1",
        granted_capabilities=req.granted_capabilities,
    )
    digest = hashlib.sha256(b"verified commit evidence").hexdigest()
    store.seed_evidence(
        ref="commit-ref",
        kind="git_commit",
        digest=digest,
        task_id="workspace-1",
        quality=1.0,
        verified=True,
    )
    omni_context = context(req)
    verifier = CouncilStoreEvidenceVerifier(store, {"code.read": ("git_commit", "artifact")})
    assert verifier(req, omni_context)
    kinds_file = tmp_path / "evidence-kinds.json"
    kinds_file.write_text(json.dumps({"code.read": ["git_commit", "artifact"]}))
    database = tmp_path / "council.sqlite"
    monkeypatch.setattr(omni_evidence, "_council_authority_database_path", lambda _path: database)
    monkeypatch.setenv(
        "CKNEXUS_COUNCIL_AUTHORITY_DB",
        "/root/.local/state/cknexus/council-authority/evidence.sqlite3",
    )
    monkeypatch.setenv("CKNEXUS_OMNI_EVIDENCE_KINDS_FILE", str(kinds_file))
    assert verify(req, omni_context)
    wrong_task = type(req)(
        execution_id=req.execution_id,
        correlation_id=req.correlation_id,
        skill_id=req.skill_id,
        skill_version=req.skill_version,
        executor=req.executor,
        goal=req.goal,
        plan_step=req.plan_step,
        inputs={
            "evidence_refs": ["commit-ref"],
            "evidence_task_id": "another-workspace",
        },
        workspace_id="another-workspace",
        granted_capabilities=req.granted_capabilities,
    )
    assert not verifier(wrong_task, omni_context)
    assert not CouncilStoreEvidenceVerifier(store, {"code.read": ("artifact",)})(req, omni_context)


def test_verify_rejects_database_outside_approved_storage_roots(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    outside_database = tmp_path / "outside" / "council.sqlite"
    outside_database.parent.mkdir()
    outside_database.touch()
    kinds_file = tmp_path / "evidence-kinds.json"
    kinds_file.write_text(json.dumps({"code.read": ["git_commit"]}))
    monkeypatch.setenv("CKNEXUS_COUNCIL_AUTHORITY_DB", str(outside_database))
    monkeypatch.setenv("CKNEXUS_OMNI_EVIDENCE_KINDS_FILE", str(kinds_file))

    req = request()
    assert not verify(req, context(req))
