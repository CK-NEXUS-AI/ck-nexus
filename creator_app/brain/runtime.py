"""Composition layer for CK-NEXUS planning, knowledge and bounded learning."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from creator_app.capability_fabric.catalog import CapabilityCatalog
from creator_app.control_plane.orchestrator import ControlPlaneOrchestrator
from creator_app.global_knowledge.ebook_store import EbookKnowledgeStore
from creator_app.n8n_intelligence.learning import AgentLearningMemory

from .journal import BrainJournal


class BrainRuntime:
    """Single facade over existing capabilities; no independent authority plane."""

    def __init__(
        self,
        *,
        root: str | Path,
        journal_path=None,
        task_db_path=None,
        knowledge_db_path=None,
        evidence_dir=None,
        orchestrator=None,
        cloud_worker=None,
    ):
        self.root = Path(root)
        self.catalog_path = self.root / "config" / "capability_catalog.json"
        self.journal_path = Path(
            journal_path or os.getenv("CKNEXUS_BRAIN_DB", self.root / ".state" / "brain.sqlite3")
        )
        self.task_db_path = Path(
            task_db_path
            or os.getenv("CKNEXUS_TASK_DB", self.root / ".state" / "control-plane.sqlite3")
        )
        self.knowledge_db_path = Path(
            knowledge_db_path
            or os.getenv("CKNEXUS_EBOOK_DB", "/var/lib/cknexus-knowledge/ebooks.sqlite3")
        )
        self.evidence_dir = Path(evidence_dir or self.root / "evidence" / "auto_dev")
        self.orchestrator = orchestrator or ControlPlaneOrchestrator()
        self.cloud_worker = cloud_worker

    def _catalog(self):
        return CapabilityCatalog.load(self.catalog_path)

    def _open_task_count(self):
        if not self.task_db_path.is_file():
            return None
        uri = f"file:{self.task_db_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as db:
            exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='control_plane_tasks'"
            ).fetchone()
            if exists is None:
                return 0
            row = db.execute(
                "SELECT COUNT(*) FROM control_plane_tasks WHERE state IN ('queued','running')"
            ).fetchone()
        return int(row[0])

    def status(self):
        try:
            catalog = self._catalog()
            artifacts = catalog.list()
            catalog_state = "available"
            classes = {}
            statuses = {}
            for item in artifacts:
                classes[item.artifact_class.value] = classes.get(item.artifact_class.value, 0) + 1
                statuses[item.status.value] = statuses.get(item.status.value, 0) + 1
        except (OSError, ValueError, KeyError) as exc:
            catalog_state = f"degraded:{type(exc).__name__}"
            artifacts = ()
            classes = {}
            statuses = {}
        tasks = {"database_present": self.task_db_path.is_file(), "open_tasks": None}
        if self.task_db_path.is_file():
            try:
                tasks["open_tasks"] = self._open_task_count()
            except (OSError, sqlite3.Error):
                tasks["status"] = "unavailable"
        knowledge = {"database_present": self.knowledge_db_path.is_file(), "source_count": None}
        if self.knowledge_db_path.is_file():
            try:
                documents = EbookKnowledgeStore(self.knowledge_db_path).list_documents_readonly()
                knowledge["source_count"] = len(documents)
                knowledge["active_source_count"] = sum(
                    not bool(item.get("revoked", False)) for item in documents
                )
                knowledge["revoked_source_count"] = sum(
                    bool(item.get("revoked", False)) for item in documents
                )
            except (OSError, ValueError):
                knowledge["status"] = "unavailable"
        journal = {"database_present": self.journal_path.is_file()}
        if self.journal_path.is_file():
            try:
                journal.update(BrainJournal(self.journal_path).summary(limit=3))
            except (OSError, ValueError):
                journal["status"] = "unavailable"
        else:
            journal.update({"observation_count": 0, "pending_improvement_candidates": 0})
        return {
            "brain_status": "ready_for_planning" if catalog_state == "available" else "degraded",
            "architecture": "CK-NEXUS_BRAIN_FABRIC_V1",
            "catalog": {
                "status": catalog_state,
                "artifact_count": len(artifacts),
                "class_counts": classes,
                "status_counts": statuses,
            },
            "planner": {
                "status": "available",
                "implementation": "ControlPlaneOrchestrator",
                "execution_performed": False,
            },
            "task_queue": tasks,
            "knowledge": {**knowledge, "retrieval_mode": "lexical", "rights_gated_ingestion": True},
            "learning_journal": journal,
            "cloud_worker": (
                self.cloud_worker.status()
                if self.cloud_worker is not None
                else {"provider": "github_actions", "enabled": False, "configured": False}
            ),
            "learning": {
                "status": "evidence_derived",
                "raw_prompts_stored": False,
                "self_reported_outcomes_promoted": False,
            },
            "authority": {
                "core": "CK-NEXUS Core L3 only",
                "external_tools": "NONE",
                "external_mutation_authorized": False,
            },
            "production_status": "NO-GO",
            "q10_status": "NOT_VERIFIED",
            "release_evidence": False,
        }

    def plan(self, request: str, *, priority=2, context=""):
        if not isinstance(request, str) or not request.strip() or len(request) > 20000:
            raise ValueError("request must be non-empty and at most 20000 characters")
        if priority not in {1, 2, 3}:
            raise ValueError("priority must be 1, 2 or 3")
        graph = self.orchestrator.plan(request, priority=priority, context=context)
        return {
            "plan": graph.as_dict(),
            "queue_payloads": self.orchestrator.queue_payloads(graph),
            "execution_state": "PLANNED_NOT_EXECUTED",
            "external_mutation_authorized": False,
            "production_status": "NO-GO",
            "release_evidence": False,
        }

    def learning_context(self, task):
        return AgentLearningMemory(self.evidence_dir, max_records=20).context_for(task)

    def record_observation(self, **kwargs):
        return BrainJournal(self.journal_path).record_observation(**kwargs)

    def propose_improvement(self, **kwargs):
        return BrainJournal(self.journal_path).propose_improvement(**kwargs)

    def journal_summary(self):
        if not self.journal_path.is_file():
            return {
                "observation_count": 0,
                "pending_improvement_candidates": 0,
                "raw_prompts_or_outputs_stored": False,
            }
        return BrainJournal(self.journal_path).summary()

    def cloud_worker_status(self):
        if self.cloud_worker is None:
            return {"provider": "github_actions", "enabled": False, "configured": False}
        return self.cloud_worker.status()

    def dispatch_cloud_worker(self, *, task_kind, subject_sha):
        if self.cloud_worker is None:
            raise RuntimeError("cloud worker adapter is not configured")
        return self.cloud_worker.dispatch(task_kind=task_kind, subject_sha=subject_sha)

    def cloud_worker_result(self, *, request_id):
        if self.cloud_worker is None:
            raise RuntimeError("cloud worker adapter is not configured")
        return self.cloud_worker.get_result(request_id=request_id)

    def knowledge_search(self, query, *, limit=8):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        if not self.knowledge_db_path.is_file():
            return []
        hits = EbookKnowledgeStore(self.knowledge_db_path).search_readonly(query, limit=limit)
        return [
            {
                "chunk_id": h.chunk_id,
                "source_sha256": h.source_sha256,
                "title": h.title,
                "chapter_id": h.chapter_id,
                "chunk_order": h.chunk_order,
                "text": h.text,
            }
            for h in hits
        ]
