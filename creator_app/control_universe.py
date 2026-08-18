from __future__ import annotations

import asyncio
import hmac
import json
import os
import resource
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from creator_app.catalog import list_agent_cards
from creator_app.runtime_binding import runtime_binding_status

WEB_DIR = Path(__file__).resolve().parent / "web"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
    except (OSError, json.JSONDecodeError):
        return []
    return records


def _source_identity() -> dict[str, str]:
    sha = (
        os.getenv("CKNEXUS_SOURCE_SHA")
        or os.getenv("CKNEXUS_BUILD_SHA")
        or os.getenv("GITHUB_SHA")
        or "UNKNOWN"
    )
    return {
        "sha": sha,
        "verification": "RUNTIME_DECLARED" if sha != "UNKNOWN" else "UNKNOWN",
    }


def _production_status(gate: object) -> dict[str, str]:
    reason = str(gate or "Production gate status is unavailable.")
    upper = reason.upper()
    if "NO-GO" in upper or "BLOCKED" in upper:
        current = "NO-GO"
    elif "PRODUCTION_READY" in upper or "PRODUCTION READY" in upper:
        current = "READY_CLAIM_REQUIRES_EVIDENCE"
    else:
        current = "UNKNOWN"
    return {"status": current, "reason": reason}


def _provider_projection(app: FastAPI) -> list[dict[str, Any]]:
    providers: list[dict[str, Any]] = []
    for item in app.state.provider_router.statuses():
        providers.append(
            {
                "name": item.name,
                "kind": item.kind.value,
                "available": item.available,
                "circuit_open": item.circuit_open,
                "capabilities": sorted(item.capabilities.features),
                "models": list(item.capabilities.models),
            }
        )
    return providers


def _agent_projection() -> list[dict[str, Any]]:
    agents: list[dict[str, Any]] = []
    for item in list_agent_cards():
        agents.append(
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "runtime_state": "UNKNOWN",
                "progress": {"mode": "indeterminate"},
            }
        )
    return agents


def _process_telemetry() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "memory_max_rss_kb": int(usage.ru_maxrss),
        "cpu_percent": None,
        "gpu_percent": None,
        "tokens_per_second": None,
        "estimated_cost_usd": None,
        "availability": {
            "memory_max_rss_kb": "MEASURED",
            "cpu_percent": "NOT_COLLECTED",
            "gpu_percent": "NOT_COLLECTED",
            "tokens_per_second": "NOT_COLLECTED",
            "estimated_cost_usd": "NOT_COLLECTED",
        },
    }


def _event_from_ledger(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    sequence = int(record.get("sequence") or 0)
    task_id = str(payload.get("task_id") or payload.get("taskId") or "GLOBAL")
    run_id = str(
        payload.get("run_id")
        or payload.get("execution_id")
        or payload.get("executionId")
        or "UNKNOWN"
    )
    return {
        "schema_version": "1.0",
        "seq": sequence,
        "event_id": f"LEDGER-{sequence:08d}",
        "event_type": str(record.get("event_type") or "ledger.recorded"),
        "task_id": task_id,
        "run_id": run_id,
        "state": {"previous": None, "current": "RECORDED"},
        "governance": {
            "policy": payload.get("policy_version") or payload.get("policy"),
            "decision": payload.get("decision") or payload.get("result"),
        },
        "evidence_ref": record.get("hash"),
        "timestamp": record.get("at"),
        "payload": payload,
    }


def install_control_universe(app: FastAPI) -> None:
    settings = app.state.settings

    async def require_access(
        authorization: str | None = Header(default=None),
    ) -> None:
        expected = settings.access_token
        if not expected:
            return
        supplied = ""
        if authorization and authorization.startswith("Bearer "):
            supplied = authorization.removeprefix("Bearer ").strip()
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED",
                    "message": "A valid CK-NEXUS access token is required.",
                },
            )

    @app.get("/control-universe", include_in_schema=False)
    async def control_universe_page() -> FileResponse:
        return FileResponse(WEB_DIR / "control-universe.html")

    @app.get(
        "/api/control-universe/overview",
        dependencies=[Depends(require_access)],
    )
    async def control_universe_overview() -> dict[str, Any]:
        agnes = app.state.agnes.status()
        ledger = agnes["ledger"]
        database_ready = app.state.store.ping()
        binding = {"postgres": None, "redis": None}
        if app.state.runtime_binding_required:
            binding = await runtime_binding_status()

        return {
            "schema_version": "1.0",
            "product": {
                "name": "CK-NEXUS Cognitive Control Universe",
                "version": settings.app_version,
                "environment": settings.environment,
            },
            "source_identity": _source_identity(),
            "production": _production_status(agnes.get("production_gate")),
            "runtime": {
                "database": "READY" if database_ready else "UNAVAILABLE",
                "postgres_binding": (
                    "READY"
                    if binding.get("postgres")
                    else "UNAVAILABLE"
                    if app.state.runtime_binding_required
                    else "NOT_REQUIRED"
                ),
                "redis_binding": (
                    "READY"
                    if binding.get("redis")
                    else "UNAVAILABLE"
                    if app.state.runtime_binding_required
                    else "NOT_REQUIRED"
                ),
                "execution_kernel": agnes.get("execution_kernel", {}),
            },
            "governance": {
                "policy": agnes.get("policy", {}),
                "inference": agnes.get("inference", {}),
                "autonomous_dev_pipeline": agnes.get("autonomous_dev_pipeline", {}),
            },
            "evidence": {
                "kind": "HASH_CHAINED_APPEND_ONLY_LEDGER",
                "valid": bool(ledger.get("valid")),
                "entries": int(ledger.get("entries") or 0),
                "last_hash": ledger.get("last_hash"),
                "immutability_claim": "NOT_CLAIMED",
            },
            "providers": _provider_projection(app),
            "agents": _agent_projection(),
            "telemetry": _process_telemetry(),
            "capabilities": {
                "semantic_zoom": True,
                "evidence_stream": True,
                "historical_replay": True,
                "pause_task": False,
                "resume_task": False,
                "cancel_task": False,
                "retry_node": False,
                "reason": "No authoritative task-control adapter is bound to this UI yet.",
            },
        }

    @app.get(
        "/api/control-universe/graph",
        dependencies=[Depends(require_access)],
    )
    async def control_universe_graph() -> dict[str, Any]:
        overview = await control_universe_overview()
        providers = overview["providers"]
        model_ready = any(item["available"] and not item["circuit_open"] for item in providers)
        evidence = overview["evidence"]
        runtime = overview["runtime"]
        nodes = [
            {"id": "user", "scale": 12, "type": "system", "state": "AVAILABLE"},
            {"id": "governor", "scale": 10, "type": "decision", "state": "AVAILABLE"},
            {"id": "workflow", "scale": 8, "type": "workflow", "state": "AVAILABLE"},
            {"id": "agents", "scale": 6, "type": "agent", "state": "AVAILABLE"},
            {
                "id": "model",
                "scale": 5,
                "type": "model",
                "state": "AVAILABLE" if model_ready else "UNAVAILABLE",
            },
            {
                "id": "execution",
                "scale": 3,
                "type": "node",
                "state": "AVAILABLE" if runtime["database"] == "READY" else "DEGRADED",
            },
            {"id": "verification", "scale": 2, "type": "verification", "state": "AVAILABLE"},
            {
                "id": "evidence",
                "scale": 1,
                "type": "evidence",
                "state": "VERIFIED" if evidence["valid"] else "FAILED",
            },
        ]
        edges = [
            ["user", "governor"],
            ["governor", "workflow"],
            ["workflow", "agents"],
            ["agents", "model"],
            ["model", "execution"],
            ["execution", "verification"],
            ["verification", "evidence"],
        ]
        return {
            "graph_kind": "RUNTIME_CAPABILITY_PROJECTION",
            "authoritative_task_graph": False,
            "nodes": nodes,
            "edges": edges,
        }

    @app.get(
        "/api/control-universe/events",
        dependencies=[Depends(require_access)],
    )
    async def control_universe_events(
        after_seq: int = Query(default=0, ge=0),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> dict[str, Any]:
        path = app.state.agnes.ledger.path
        events = [
            _event_from_ledger(item)
            for item in _read_jsonl(path)
            if int(item.get("sequence") or 0) > after_seq
        ]
        return {
            "events": events[:limit],
            "last_seq": events[min(len(events), limit) - 1]["seq"] if events else after_seq,
        }

    @app.get(
        "/api/control-universe/evidence",
        dependencies=[Depends(require_access)],
    )
    async def control_universe_evidence(
        after_seq: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        verification = app.state.agnes.ledger.verify()
        records = [
            item
            for item in _read_jsonl(app.state.agnes.ledger.path)
            if int(item.get("sequence") or 0) > after_seq
        ]
        return {
            "ledger": verification.as_dict(),
            "records": records[:limit],
            "storage_claim": "HASH_CHAINED_APPEND_ONLY_API",
            "immutability_claim": "NOT_CLAIMED",
        }

    @app.get(
        "/api/control-universe/agents/{agent_id}/inspect",
        dependencies=[Depends(require_access)],
    )
    async def control_universe_agent_inspect(agent_id: str) -> dict[str, Any]:
        cards = {item.id: item for item in list_agent_cards()}
        card = cards.get(agent_id)
        if card is None:
            raise HTTPException(status_code=404, detail={"error": "AGENT_NOT_FOUND"})
        return {
            "agent": card.model_dump(),
            "runtime_state": "UNKNOWN",
            "current_node": None,
            "current_tool": None,
            "progress": {"mode": "indeterminate"},
            "inspection_channel": "READ_ONLY",
            "execution_mutation": False,
        }

    @app.post(
        "/api/control-universe/tasks/{task_id}/commands/{command}",
        dependencies=[Depends(require_access)],
    )
    async def control_universe_command(task_id: str, command: str) -> dict[str, Any]:
        del task_id
        supported = {"pause", "resume", "cancel", "retry"}
        if command not in supported:
            raise HTTPException(status_code=404, detail={"error": "COMMAND_NOT_FOUND"})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "CONTROL_ADAPTER_UNAVAILABLE",
                "message": (
                    "The current CK-NEXUS runtime does not expose an authoritative "
                    "task-control adapter for this command. The UI fails closed."
                ),
            },
        )

    async def event_stream(after_seq: int) -> AsyncIterator[str]:
        cursor = after_seq
        while True:
            records = _read_jsonl(app.state.agnes.ledger.path)
            fresh = [item for item in records if int(item.get("sequence") or 0) > cursor]
            if fresh:
                for item in fresh:
                    event = _event_from_ledger(item)
                    cursor = int(event["seq"])
                    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
                    yield f"id: {cursor}\nevent: runtime\ndata: {payload}\n\n"
            else:
                yield ": keepalive\n\n"
            await asyncio.sleep(1.0)

    @app.get(
        "/api/control-universe/stream",
        dependencies=[Depends(require_access)],
    )
    async def control_universe_stream(
        after_seq: int = Query(default=0, ge=0),
    ) -> StreamingResponse:
        return StreamingResponse(
            event_stream(after_seq),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
