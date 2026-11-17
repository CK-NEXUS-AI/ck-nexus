"""Local, read-only CK-NEXUS assessment prototype. Never issues a certificate."""

from __future__ import annotations

import hashlib
import json

# subprocess is restricted to a fixed local command allowlist; shell execution is disabled.
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="CK-NEXUS Certification Portal", version="0.2.0-assessment-demo")
ROOT = Path(__file__).resolve().parent.parent
_demo_private_key = Ed25519PrivateKey.generate()
_demo_public_key = (
    _demo_private_key.public_key()
    .public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    .hex()
)


class OwnerSignoff(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    role: str = Field(min_length=2, max_length=120)
    consent: bool
    subject_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_id: str = Field(min_length=1, max_length=80)


def _run_fixed(args: list[str], timeout: int = 20) -> tuple[int, str]:
    """Run only allowlisted local commands; request data can never select a command."""
    allowed = {
        ("git", "rev-parse", "HEAD"),
        ("git", "rev-parse", "--abbrev-ref", "HEAD"),
        ("git", "status", "--porcelain"),
    }
    if tuple(args) not in allowed:
        return 126, "COMMAND_NOT_ALLOWLISTED"
    try:
        # Exact command allowlist; shell=False; bounded timeout.
        p = subprocess.run(  # nosec B603
            args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
        return p.returncode, (p.stdout + p.stderr)[-4000:]
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s"
    except Exception as exc:  # report the failure as evidence, never as a pass
        return 125, f"{type(exc).__name__}: {exc}"


def assess_local() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(control: str, passed: bool, detail: str) -> None:
        checks.append(
            {"control": control, "result": "PASS" if passed else "FAIL", "detail": detail[:1200]}
        )

    required = [
        "pyproject.toml",
        "uv.lock",
        "creator_app/unified.py",
        "docs/UNIVERSAL_AI_OPERATING_STANDARD_V2_DRAFT.md",
        "docs/CERTIFICATION_PORTAL_SPEC_DRAFT.md",
    ]
    missing = [p for p in required if not (ROOT / p).is_file()]
    record(
        "CKN-CORE-001_REQUIRED_FILES",
        not missing,
        "All required files present" if not missing else f"Missing: {missing}",
    )

    code, out = _run_fixed(["git", "rev-parse", "HEAD"])
    sha = out.strip().splitlines()[0] if code == 0 and out.strip() else None
    record("CKN-SOURCE-001_COMMIT_ID", bool(sha and len(sha) == 40), f"HEAD={sha}" if sha else out)

    code, out = _run_fixed(["git", "status", "--porcelain"])
    clean = code == 0 and not out.strip()
    record(
        "CKN-SOURCE-002_CLEAN_TREE",
        clean,
        "Working tree clean" if clean else f"Dirty/unavailable: {out.strip()[:800]}",
    )

    # Compile source in memory: compileall writes __pycache__ into the checkout.
    try:
        for source in (ROOT / "certification_portal").glob("*.py"):
            compile(source.read_text(encoding="utf-8"), str(source), "exec")
        record("CKN-PORTAL-001_COMPILE", True, "Portal Python sources compiled in memory")
    except (OSError, SyntaxError, UnicodeError) as exc:
        record("CKN-PORTAL-001_COMPILE", False, f"{type(exc).__name__}: {exc}")

    # A document status-line edit is not proof of adoption. Until a separately
    # authenticated adoption verifier exists, this gate is deliberately closed.
    record(
        "CKN-GOV-001_POLICY_ADOPTION",
        False,
        "BLOCKED: no independently verified owner adoption and Policy Kernel enforcement evidence",
    )

    mandatory_failed = any(c["result"] != "PASS" for c in checks)
    result = (
        "NOT_CERTIFIED" if mandatory_failed else "ASSESSMENT_PASS_PENDING_INDEPENDENT_VERIFICATION"
    )
    manifest = {
        "assessment_type": "LOCAL_READ_ONLY_DEMO",
        "profile_id": "CKNEXUS-CORE-v0.1-demo",
        "profile_version": "0.1.0",
        "subject": str(ROOT),
        "subject_commit": sha,
        "assessed_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "result": result,
        "limitations": [
            "Local self-assessment only; no independent verifier is connected.",
            "Dirty worktree blocks a passing conformance result.",
            "Policy V2 is a draft and has not been adopted.",
            "No certificate is issued by this prototype.",
        ],
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest["evidence_manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest


def _load_owner_signoff_subject() -> dict[str, Any]:
    """Return only a candidate manifest whose listed files still match exactly."""
    manifest_path = (
        ROOT / "certification_portal/signoff-candidates/owner-signoff-subject-manifest-v4.json"
    )
    try:
        if manifest_path.is_symlink():
            raise ValueError("manifest path must not be a symlink")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("branch") != _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]):
            raise ValueError("manifest branch does not match this checkout")
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("manifest file list is empty")
        for item in files:
            relative = Path(item["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("manifest contains an unsafe path")
            target = ROOT / relative
            resolved = target.resolve(strict=True)
            if target.is_symlink() or not resolved.is_relative_to(ROOT.resolve()):
                raise ValueError("manifest path escapes the repository or uses a symlink")
            raw = resolved.read_bytes()
            if len(raw) != item["size"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError(f"manifest file mismatch: {relative.as_posix()}")
        claimed = manifest.get("subject_sha256")
        payload = {
            key: manifest[key]
            for key in ("subject", "profile_id", "branch", "base_commit", "files")
        }
        actual = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if claimed != actual:
            raise ValueError("manifest subject digest is invalid")
        return {
            "subject_digest": actual,
            "profile_id": manifest["profile_id"],
            "file_count": len(files),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503, detail="Owner sign-off subject is not ready or has changed"
        ) from exc


def _git_output(args: list[str]) -> str:
    code, output = _run_fixed(args)
    if code != 0:
        raise ValueError("git source identity unavailable")
    return output.strip()


@app.get("/api/owner-signoff-subject")
def owner_signoff_subject() -> dict[str, Any]:
    """Expose a digest only after checking the candidate manifest and every file."""
    return _load_owner_signoff_subject()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "ASSESSMENT_DEMO", "certificate_issuance": "disabled"}


@app.get("/api/demo-key")
def demo_key() -> dict[str, str]:
    return {
        "key_id": "ephemeral-demo-key",
        "algorithm": "Ed25519",
        "public_key_hex": _demo_public_key,
        "trust": "NON_PRODUCTION_EPHEMERAL",
    }


@app.post("/api/assess/local")
def assess_endpoint() -> dict[str, Any]:
    """Run bounded, read-only checks against this local checkout only."""
    return assess_local()


@app.post("/api/owner-signoff-preview")
def owner_signoff_preview(data: OwnerSignoff) -> JSONResponse:
    if not data.consent:
        raise HTTPException(status_code=400, detail="Owner consent is required")
    body: dict[str, Any] = {
        "status": "OWNER_SIGNOFF_PREVIEW_ONLY",
        "full_name": data.full_name,
        "role": data.role,
        "subject_digest": data.subject_digest,
        "profile_id": data.profile_id,
        "signed_at": datetime.now(UTC).isoformat(),
        "notice": (
            "Demo preview only; identity authentication and legal-signature "
            "requirements are not implemented."
        ),
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["digest"] = hashlib.sha256(canonical).hexdigest()
    body["demo_signature"] = _demo_private_key.sign(canonical).hex()
    body["key_id"] = "ephemeral-demo-key"
    return JSONResponse(body)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).with_name("index.html")).read_text(encoding="utf-8")
