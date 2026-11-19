"""Evidence verification adapter backed by the existing Council Authority SQLite registry."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from creator_app.agnes.execution.omni import OMNIExecutionContext
from creator_app.agnes.execution.request import SkillExecutionRequest
from creator_app.council_authority.storage import AuthorityStore


class CouncilStoreEvidenceVerifier:
    """Require evidence to be verified, unrevoked, task-bound, and policy-allowed."""

    def __init__(self, store: AuthorityStore, allowed_kinds: dict[str, tuple[str, ...]]):
        self.store = store
        self.allowed_kinds = {
            capability: frozenset(kinds) for capability, kinds in allowed_kinds.items()
        }

    def __call__(self, request: SkillExecutionRequest, context: OMNIExecutionContext) -> bool:
        allowed = self.allowed_kinds.get(context.capability_id, frozenset())
        if not allowed:
            return False
        refs = request.inputs.get("evidence_refs")
        task_id = request.workspace_id or request.correlation_id
        declared_task = request.inputs.get("evidence_task_id")
        if (
            not isinstance(refs, (list, tuple))
            or not refs
            or any(not isinstance(ref, str) or not ref for ref in refs)
            or len(set(refs)) != len(refs)
            or declared_task != task_id
        ):
            return False
        try:
            with self.store._db() as db:
                for ref in refs:
                    row = db.execute(
                        "SELECT kind,digest,task_id,verified,revoked,quality "
                        "FROM evidence WHERE ref=?",
                        (ref,),
                    ).fetchone()
                    if (
                        row is None
                        or row["kind"] not in allowed
                        or row["task_id"] != task_id
                        or not row["verified"]
                        or row["revoked"]
                        or float(row["quality"]) <= 0
                        or not self._valid_sha256(row["digest"])
                    ):
                        return False
            return True
        except Exception:
            return False

    @staticmethod
    def _valid_sha256(value: Any) -> bool:
        if not isinstance(value, str) or len(value) != 64:
            return False
        try:
            int(value, 16)
        except ValueError:
            return False
        return True


def verify(request: SkillExecutionRequest, context: OMNIExecutionContext) -> bool:
    """Configured callback for scripts/run_omni_issuer.py; missing config denies."""
    database = Path(os.environ.get("CKNEXUS_COUNCIL_AUTHORITY_DB", ""))
    policy_path = Path(os.environ.get("CKNEXUS_OMNI_EVIDENCE_KINDS_FILE", ""))
    if (
        not str(database)
        or not database.is_file()
        or database.is_symlink()
        or not str(policy_path)
        or not policy_path.is_file()
        or policy_path.is_symlink()
    ):
        return False
    try:
        raw = json.loads(policy_path.read_text())
        if not isinstance(raw, dict) or not raw:
            return False
        kinds: dict[str, tuple[str, ...]] = {}
        for capability, values in raw.items():
            if (
                not isinstance(capability, str)
                or not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) and value for value in values)
            ):
                return False
            kinds[capability] = tuple(values)
        return CouncilStoreEvidenceVerifier(AuthorityStore(str(database)), kinds)(request, context)
    except Exception:
        return False
