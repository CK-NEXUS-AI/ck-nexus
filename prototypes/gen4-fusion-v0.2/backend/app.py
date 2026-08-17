from __future__ import annotations

from datetime import datetime, timezone
from fastapi import FastAPI
from .claims import compile_public_claims
from .evidence import AppendOnlyEvidenceStore
from .models import EvidenceStatus, ReleaseSnapshot

app = FastAPI(title="CK-NEXUS Gen4 Fusion Prototype", version="0.2.0")
evidence_store = AppendOnlyEvidenceStore()
release_snapshot = ReleaseSnapshot(subject="DEMO-NON-PRODUCTION")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "DEMO_NON_PRODUCTION"}


@app.get("/api/system/status")
def system_status() -> dict[str, object]:
    return {
        "mode": "DEMO_NON_PRODUCTION",
        "authority": "local prototype only",
        "production": "NO_GO",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/evidence")
def evidence() -> list[dict[str, object]]:
    return [r.model_dump(mode="json") for r in evidence_store.all()]


@app.get("/api/releases/current")
def release() -> dict[str, object]:
    return release_snapshot.model_dump(mode="json")


@app.get("/api/claims/public")
def public_claims() -> dict[str, object]:
    return compile_public_claims(release_snapshot)
