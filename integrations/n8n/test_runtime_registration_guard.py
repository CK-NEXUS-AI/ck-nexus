import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from verify_runtime_registration import RegistrationError, verify


def _workflow(path: Path, *, route: str, webhook_id: str) -> Path:
    data = {
        "name": "test",
        "nodes": [
            {
                "id": "webhook",
                "name": "Mission Intake",
                "type": "n8n-nodes-base.webhook",
                "webhookId": webhook_id,
                "parameters": {"httpMethod": "POST", "path": route},
            }
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _db(path: Path, rows: list[tuple[str, str, str, str, str | None]]) -> Path:
    con = sqlite3.connect(path)
    try:
        con.execute(
            "create table webhook_entity ("
            "workflowId text not null, webhookPath text not null, method text not null, "
            "node text not null, webhookId text, pathLength integer)"
        )
        con.executemany(
            "insert into webhook_entity(workflowId,webhookPath,method,node,webhookId) "
            "values(?,?,?,?,?)",
            rows,
        )
        con.commit()
    finally:
        con.close()
    return path


def test_accepts_exact_short_registration(tmp_path: Path) -> None:
    workflow = _workflow(
        tmp_path / "workflow.json", route="ck-nexus/super-agent", webhook_id="stable"
    )
    db = _db(
        tmp_path / "db.sqlite", [("wf", "ck-nexus/super-agent", "POST", "Mission Intake", None)]
    )
    result = verify(db, [workflow])
    assert result["ok"] is True
    assert result["stale"] == []


def test_rejects_missing_short_registration(tmp_path: Path) -> None:
    workflow = _workflow(
        tmp_path / "workflow.json", route="ck-nexus/super-agent", webhook_id="stable"
    )
    db = _db(tmp_path / "db.sqlite", [])
    with pytest.raises(RegistrationError, match="missing"):
        verify(db, [workflow])


def test_rejects_stale_long_path(tmp_path: Path) -> None:
    workflow = _workflow(
        tmp_path / "workflow.json", route="ck-nexus/super-agent", webhook_id="stable"
    )
    db = _db(
        tmp_path / "db.sqlite",
        [
            ("new", "ck-nexus/super-agent", "POST", "Mission Intake", None),
            ("old", "old/mission%20intake/ck-nexus/super-agent", "POST", "Mission Intake", None),
        ],
    )
    with pytest.raises(RegistrationError, match="stale"):
        verify(db, [workflow])


def test_requires_stable_webhook_id(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path / "workflow.json", route="ck-nexus/super-agent", webhook_id="")
    db = _db(tmp_path / "db.sqlite", [])
    with pytest.raises(RegistrationError, match="missing webhookId"):
        verify(db, [workflow])
