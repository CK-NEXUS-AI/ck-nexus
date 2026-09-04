from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from creator_app.agnes_ledger import AppendOnlyLedger


class SignerType(StrEnum):
    SYSTEM = "SYSTEM_SIGNER"
    HUMAN_REVIEWER = "HUMAN_REVIEWER"
    OWNER = "OWNER_SIGNER"


class SignatureStatus(StrEnum):
    UNSIGNED = "UNSIGNED"
    CRYPTOGRAPHICALLY_VERIFIED = "CRYPTOGRAPHICALLY_VERIFIED"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class EvidenceSubject:
    repository: str
    commit: str
    tree: str
    environment: str
    scanner: str
    scanner_version: str
    run_id: str | None = None


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = root / relative_path
    if candidate.is_symlink():
        raise ValueError(f"symlink evidence artifact is not allowed: {relative_path}")
    resolved = candidate.resolve(strict=True)
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"artifact escapes evidence root: {relative_path}")
    if not resolved.is_file():
        raise ValueError(f"artifact is not a regular file: {relative_path}")
    return resolved


def build_manifest(
    *,
    root: Path,
    subject: EvidenceSubject,
    artifacts: Iterable[str],
    observed_at: str | None = None,
) -> dict[str, Any]:
    unique = sorted(set(artifacts))
    if not unique:
        raise ValueError("at least one evidence artifact is required")
    rows = []
    for relative_path in unique:
        path = _safe_file(root, relative_path)
        rows.append(
            {
                "path": relative_path,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    payload = {
        "schema_version": 1,
        "kind": "CK_NEXUS_EVIDENCE_MANIFEST",
        "observed_at": observed_at or datetime.now(UTC).isoformat(),
        "subject": asdict(subject),
        "artifacts": rows,
        "trust": {
            "system_signature": SignatureStatus.UNSIGNED.value,
            "independent_human_review": "PENDING",
            "owner_signoff": "PENDING",
            "production_effect": "NONE",
        },
    }
    return {**payload, "manifest_sha256": sha256_json(payload)}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    claimed_digest = str(manifest.get("manifest_sha256") or "")
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    actual_digest = sha256_json(payload)
    if claimed_digest != actual_digest:
        failures.append("manifest digest mismatch")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        failures.append("manifest artifacts missing")
    else:
        for row in artifacts:
            if not isinstance(row, dict):
                failures.append("invalid artifact row")
                continue
            relative_path = str(row.get("path") or "")
            try:
                path = _safe_file(root, relative_path)
            except (OSError, ValueError) as exc:
                failures.append(f"{relative_path}: {exc}")
                continue
            if sha256_file(path) != row.get("sha256"):
                failures.append(f"{relative_path}: sha256 mismatch")
            if path.stat().st_size != row.get("size_bytes"):
                failures.append(f"{relative_path}: size mismatch")

    return {
        "valid": not failures,
        "manifest_sha256": actual_digest,
        "failures": failures,
    }


class EvidenceCustodyLedger:
    def __init__(self, path: Path) -> None:
        self.ledger = AppendOnlyLedger(path)

    def append(
        self,
        *,
        action: str,
        actor_type: SignerType,
        actor_id: str,
        manifest_sha256: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "action": action,
            "actor_type": actor_type.value,
            "actor_id": actor_id,
            "manifest_sha256": manifest_sha256,
            "metadata": metadata or {},
        }
        return self.ledger.append("evidence_custody", payload)

    def verify(self) -> dict[str, Any]:
        return self.ledger.verify().as_dict()

    def export(self, output: Path) -> dict[str, Any]:
        state = self.ledger.verify()
        if not state.valid:
            raise RuntimeError(f"custody ledger corrupt: {state.error}")
        entries: list[dict[str, Any]] = []
        if self.ledger.path.exists():
            with self.ledger.path.open("r", encoding="utf-8") as handle:
                entries = [json.loads(line) for line in handle if line.strip()]
        payload = {
            "schema_version": 1,
            "kind": "CK_NEXUS_CHAIN_OF_CUSTODY",
            "entries": entries,
            "final_hash": state.last_hash,
        }
        write_json(output, payload)
        return payload


def verify_chain_export(payload: dict[str, Any]) -> dict[str, Any]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return {"valid": False, "entries": 0, "error": "entries missing"}
    previous_hash: str | None = None
    for index, row in enumerate(entries, start=1):
        if not isinstance(row, dict):
            return {"valid": False, "entries": index - 1, "error": "invalid row"}
        if row.get("sequence") != index:
            return {"valid": False, "entries": index - 1, "error": "sequence mismatch"}
        if row.get("previous_hash") != previous_hash:
            return {"valid": False, "entries": index - 1, "error": "hash chain mismatch"}
        claimed = str(row.get("hash") or "")
        base = {key: value for key, value in row.items() if key != "hash"}
        actual = AppendOnlyLedger._digest(base)
        if not claimed or claimed != actual:
            return {"valid": False, "entries": index - 1, "error": "record digest mismatch"}
        previous_hash = claimed
    if payload.get("final_hash") != previous_hash:
        return {"valid": False, "entries": len(entries), "error": "final hash mismatch"}
    return {"valid": True, "entries": len(entries), "last_hash": previous_hash, "error": None}


def unsigned_signature_envelope(manifest_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "CK_NEXUS_SIGNATURE_ENVELOPE",
        "manifest_sha256": manifest_sha256,
        "signers": [
            {"type": SignerType.SYSTEM.value, "status": SignatureStatus.UNSIGNED.value},
            {"type": SignerType.HUMAN_REVIEWER.value, "status": "PENDING"},
            {"type": SignerType.OWNER.value, "status": "PENDING"},
        ],
        "release_gate_effect": "NONE",
        "production_authorized": False,
    }


def evaluate_signature_policy(envelope: dict[str, Any]) -> dict[str, Any]:
    statuses = {
        str(item.get("type")): str(item.get("status"))
        for item in envelope.get("signers", [])
        if isinstance(item, dict)
    }
    return {
        "system_integrity": (
            statuses.get(SignerType.SYSTEM.value)
            == SignatureStatus.CRYPTOGRAPHICALLY_VERIFIED.value
        ),
        "independent_human_review": (
            statuses.get(SignerType.HUMAN_REVIEWER.value)
            == SignatureStatus.CRYPTOGRAPHICALLY_VERIFIED.value
        ),
        "owner_signoff": (
            statuses.get(SignerType.OWNER.value)
            == SignatureStatus.CRYPTOGRAPHICALLY_VERIFIED.value
        ),
        "release_gate_effect": "NONE",
        "production_authorized": False,
    }


_MIN_SAFE_COSIGN = (3, 1, 3)


def _cosign_version(binary: str) -> tuple[int, int, int]:
    proc = subprocess.run(
        [binary, "version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    combined = f"{proc.stdout}\n{proc.stderr}"
    match = re.search(r"\bv?(\d+)\.(\d+)\.(\d+)\b", combined)
    if proc.returncode != 0 or match is None:
        raise RuntimeError("unable to determine cosign version")
    return tuple(int(part) for part in match.groups())


def verify_cosign_bundle(
    *,
    blob: Path,
    bundle: Path,
    certificate_identity: str,
    certificate_oidc_issuer: str,
    cosign_binary: str = "cosign",
) -> dict[str, Any]:
    version = _cosign_version(cosign_binary)
    if version < _MIN_SAFE_COSIGN:
        raise RuntimeError("cosign 3.1.3 or newer is required for keyless bundle verification")

    parsed = json.loads(bundle.read_text(encoding="utf-8"))
    media_type = str(parsed.get("mediaType") or "")
    if not media_type.startswith("application/vnd.dev.sigstore.bundle"):
        raise RuntimeError("legacy/non-standard Sigstore bundle rejected")

    proc = subprocess.run(
        [
            cosign_binary,
            "verify-blob",
            str(blob),
            "--bundle",
            str(bundle),
            "--certificate-identity",
            certificate_identity,
            "--certificate-oidc-issuer",
            certificate_oidc_issuer,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "valid": proc.returncode == 0,
        "cosign_version": ".".join(str(part) for part in version),
        "bundle_media_type": media_type,
        "certificate_identity": certificate_identity,
        "certificate_oidc_issuer": certificate_oidc_issuer,
    }
