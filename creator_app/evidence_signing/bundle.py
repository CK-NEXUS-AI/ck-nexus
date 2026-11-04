from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE_FILES = (
    "scan-manifest.json",
    "findings.json",
    "coverage.json",
    "report.md",
)
_ZERO_HASH = "0" * 64
_GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40}$")


class EvidenceBundleError(ValueError):
    """Raised when evidence identity or integrity is invalid."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_git_object(value: str, name: str) -> str:
    normalized = str(value).lower()
    if not _GIT_OBJECT_RE.fullmatch(normalized):
        raise EvidenceBundleError(f"{name} must be a 40-character lowercase Git object id")
    return normalized


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _artifact_rows(evidence_dir: Path, required_files: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative in sorted(required_files):
        path = evidence_dir / relative
        if not path.is_file():
            raise EvidenceBundleError(f"required evidence file is missing: {relative}")
        rows.append(
            {
                "path": relative,
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return rows


def _chain_entry(
    *,
    seq: int,
    previous_hash: str,
    timestamp: str,
    action: str,
    actor_type: str,
    actor_id: str,
    manifest_sha256: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    material = {
        "seq": seq,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "action": action,
        "actor": {"type": actor_type, "id": actor_id},
        "manifest_sha256": manifest_sha256,
        "metadata": metadata or {},
    }
    return {**material, "entry_hash": _sha256_bytes(_canonical_json(material).encode())}


def verify_chain(chain: dict[str, Any], expected_manifest_sha256: str | None = None) -> bool:
    entries = chain.get("entries")
    if not isinstance(entries, list) or not entries:
        return False

    previous = _ZERO_HASH
    for expected_seq, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            return False
        if entry.get("seq") != expected_seq or entry.get("previous_hash") != previous:
            return False
        material = {key: value for key, value in entry.items() if key != "entry_hash"}
        actual = _sha256_bytes(_canonical_json(material).encode())
        if entry.get("entry_hash") != actual:
            return False
        if expected_manifest_sha256 and entry.get("manifest_sha256") != expected_manifest_sha256:
            return False
        previous = actual
    return chain.get("final_hash") == previous


def append_chain_event(
    chain_path: Path,
    *,
    manifest_sha256: str,
    action: str,
    actor_type: str,
    actor_id: str,
    metadata: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    chain = json.loads(chain_path.read_text(encoding="utf-8"))
    if not verify_chain(chain, manifest_sha256):
        raise EvidenceBundleError("existing chain-of-custody is invalid")

    entries = chain["entries"]
    previous_hash = entries[-1]["entry_hash"]
    entry = _chain_entry(
        seq=len(entries) + 1,
        previous_hash=previous_hash,
        timestamp=timestamp or _utc_now(),
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        manifest_sha256=manifest_sha256,
        metadata=metadata,
    )
    entries.append(entry)
    chain["final_hash"] = entry["entry_hash"]
    chain_path.write_text(json.dumps(chain, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return entry


def _write_state(output_dir: Path, manifest_sha256: str) -> dict[str, Any]:
    state = {
        "schema_version": 1,
        "kind": "CKNEXUS_EVIDENCE_VERIFICATION_STATE",
        "manifest_sha256": manifest_sha256,
        "cryptographic_integrity": "MEASURED",
        "system_signature": {
            "status": "NOT_SIGNED",
            "provider": None,
            "bundle": None,
            "meaning": "No cryptographic signer has been verified for this manifest.",
        },
        "independent_human_review": {
            "status": "PENDING",
            "required": True,
        },
        "owner_signoff": {
            "status": "PENDING",
            "required": True,
        },
        "q10": "NOT_VERIFIED",
        "production": "NO-GO",
    }
    (output_dir / "verification-state.json").write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return state


def build_evidence_bundle(
    *,
    evidence_dir: Path,
    output_dir: Path,
    repository: str,
    subject_commit: str,
    subject_tree: str,
    scanner: str,
    scanner_version: str,
    run_id: str | None = None,
    observed_at: str | None = None,
    required_files: tuple[str, ...] = REQUIRED_EVIDENCE_FILES,
) -> dict[str, Any]:
    evidence_dir = evidence_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    commit = _validate_git_object(subject_commit, "subject_commit")
    tree = _validate_git_object(subject_tree, "subject_tree")
    artifacts = _artifact_rows(evidence_dir, required_files)

    manifest = {
        "schema_version": 1,
        "kind": "CKNEXUS_EVIDENCE_SIGNING_MANIFEST",
        "repository": repository,
        "subject": {
            "commit": commit,
            "tree": tree,
        },
        "scanner": {
            "name": scanner,
            "version": scanner_version,
        },
        "run_id": run_id,
        "observed_at": observed_at or _utc_now(),
        "artifacts": artifacts,
        "signing_target": "evidence-signing-manifest.json",
        "signature_semantics": "CRYPTOGRAPHIC_INTEGRITY_ONLY",
        "independent_human_review_required": True,
        "owner_signoff_required": True,
        "q10_authority_effect": "NONE",
        "production_effect": False,
    }
    manifest_path = output_dir / "evidence-signing-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_sha256 = _sha256_file(manifest_path)

    sums = [f"{row['sha256']}  {row['path']}" for row in artifacts]
    sums.append(f"{manifest_sha256}  evidence-signing-manifest.json")
    (output_dir / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    genesis = _chain_entry(
        seq=1,
        previous_hash=_ZERO_HASH,
        timestamp=manifest["observed_at"],
        action="EVIDENCE_BUNDLE_CREATED",
        actor_type="system",
        actor_id="ck-nexus-evidence-signing-v1",
        manifest_sha256=manifest_sha256,
        metadata={
            "artifact_count": len(artifacts),
            "signature_status": "NOT_SIGNED",
        },
    )
    chain = {
        "schema_version": 1,
        "kind": "CKNEXUS_CHAIN_OF_CUSTODY",
        "manifest_sha256": manifest_sha256,
        "entries": [genesis],
        "final_hash": genesis["entry_hash"],
    }
    (output_dir / "chain-of-custody.json").write_text(
        json.dumps(chain, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    state = _write_state(output_dir, manifest_sha256)

    return {
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "chain": chain,
        "verification_state": state,
    }


def record_system_signature(
    *,
    output_dir: Path,
    provider: str,
    bundle_filename: str,
    signer_identity: str,
    verified_at: str | None = None,
) -> dict[str, Any]:
    state_path = output_dir / "verification-state.json"
    manifest_path = output_dir / "evidence-signing-manifest.json"
    bundle_path = output_dir / bundle_filename
    if not state_path.is_file() or not manifest_path.is_file() or not bundle_path.is_file():
        raise EvidenceBundleError("manifest, verification state, and signature bundle are required")

    manifest_sha256 = _sha256_file(manifest_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("manifest_sha256") != manifest_sha256:
        raise EvidenceBundleError("verification state is bound to a different manifest")

    state["system_signature"] = {
        "status": "CRYPTOGRAPHICALLY_VERIFIED",
        "provider": provider,
        "bundle": bundle_filename,
        "bundle_sha256": _sha256_file(bundle_path),
        "signer_identity": signer_identity,
        "verified_at": verified_at or _utc_now(),
        "meaning": "Artifact integrity/signing identity verified; not independent human approval.",
    }
    state["independent_human_review"]["status"] = "PENDING"
    state["owner_signoff"]["status"] = "PENDING"
    state["q10"] = "NOT_VERIFIED"
    state["production"] = "NO-GO"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    append_chain_event(
        output_dir / "chain-of-custody.json",
        manifest_sha256=manifest_sha256,
        action="SYSTEM_SIGNATURE_VERIFIED",
        actor_type="system",
        actor_id=provider,
        metadata={
            "bundle": bundle_filename,
            "bundle_sha256": state["system_signature"]["bundle_sha256"],
            "signer_identity": signer_identity,
        },
        timestamp=state["system_signature"]["verified_at"],
    )
    return state


def verify_evidence_bundle(*, evidence_dir: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "evidence-signing-manifest.json"
    chain_path = output_dir / "chain-of-custody.json"
    state_path = output_dir / "verification-state.json"
    if not all(path.is_file() for path in (manifest_path, chain_path, state_path)):
        raise EvidenceBundleError("evidence bundle is incomplete")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha256 = _sha256_file(manifest_path)
    failures: list[str] = []

    for artifact in manifest.get("artifacts", []):
        path = evidence_dir / artifact["path"]
        if not path.is_file():
            failures.append(f"missing:{artifact['path']}")
            continue
        if _sha256_file(path) != artifact.get("sha256"):
            failures.append(f"hash_mismatch:{artifact['path']}")

    chain = json.loads(chain_path.read_text(encoding="utf-8"))
    if chain.get("manifest_sha256") != manifest_sha256:
        failures.append("chain_manifest_mismatch")
    if not verify_chain(chain, manifest_sha256):
        failures.append("chain_invalid")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("manifest_sha256") != manifest_sha256:
        failures.append("verification_state_manifest_mismatch")
    if state.get("q10") != "NOT_VERIFIED":
        failures.append("q10_boundary_changed")
    if state.get("production") != "NO-GO":
        failures.append("production_boundary_changed")

    return {
        "result": "PASS" if not failures else "FAIL",
        "manifest_sha256": manifest_sha256,
        "failures": failures,
        "system_signature": state.get("system_signature"),
        "independent_human_review": state.get("independent_human_review"),
        "owner_signoff": state.get("owner_signoff"),
        "q10": state.get("q10"),
        "production": state.get("production"),
    }
