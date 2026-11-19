from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_app.brain import BrainJournal, BrainRuntime
from creator_app.global_knowledge import ebook_store as ebook_store_module


@pytest.fixture(autouse=True)
def _allow_test_database_root(tmp_path, monkeypatch):
    monkeypatch.setattr(ebook_store_module, "_ALLOWED_DB_ROOTS", (tmp_path,))


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    payload = {
        "schema_version": "1.0.0",
        "artifacts": [
            {
                "id": "core",
                "name": "CK-NEXUS Core",
                "class": "core",
                "status": "present",
                "integration_point": "internal",
                "authority_scope": "L3",
            },
            {
                "id": "provider",
                "name": "Provider",
                "class": "ai_provider",
                "status": "partial",
                "integration_point": "gateway",
                "authority_scope": "NONE",
            },
        ],
    }
    (root / "config" / "capability_catalog.json").write_text(json.dumps(payload), encoding="utf-8")
    return root


def test_brain_status_composes_components_and_fails_closed(tmp_path):
    brain = BrainRuntime(
        root=_root(tmp_path),
        journal_path=tmp_path / "brain.sqlite3",
        task_db_path=tmp_path / "tasks.sqlite3",
        knowledge_db_path=tmp_path / "missing.sqlite3",
        evidence_dir=tmp_path / "missing",
    )
    status = brain.status()
    assert (
        status["brain_status"] == "ready_for_planning" and status["catalog"]["artifact_count"] == 2
    )
    assert (
        status["planner"]["execution_performed"] is False
        and status["authority"]["external_mutation_authorized"] is False
    )
    assert status["production_status"] == "NO-GO" and status["q10_status"] == "NOT_VERIFIED"


def test_brain_runtime_expands_tilde_for_all_database_paths(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    brain = BrainRuntime(
        root=_root(tmp_path),
        journal_path="~/state/brain.sqlite3",
        task_db_path="~/state/tasks.sqlite3",
        knowledge_db_path="~/knowledge/ebooks.sqlite3",
    )

    assert brain.journal_path == home / "state" / "brain.sqlite3"
    assert brain.task_db_path == home / "state" / "tasks.sqlite3"
    assert brain.knowledge_db_path == home / "knowledge" / "ebooks.sqlite3"


def test_brain_plan_never_executes_or_grants_authority(tmp_path):
    brain = BrainRuntime(
        root=_root(tmp_path),
        journal_path=tmp_path / "brain.sqlite3",
        task_db_path=tmp_path / "tasks.sqlite3",
        knowledge_db_path=tmp_path / "missing.sqlite3",
        evidence_dir=tmp_path / "missing",
    )
    result = brain.plan("Improve model fallback and verify tests", priority=2)
    assert result["execution_state"] == "PLANNED_NOT_EXECUTED" and len(result["plan"]["nodes"]) == 4
    assert result["external_mutation_authorized"] is False
    assert all(x["external_mutation_authorized"] is False for x in result["queue_payloads"])


def test_journal_stores_fingerprint_not_raw_task_and_never_claims_verification(tmp_path):
    db = tmp_path / "brain.sqlite3"
    journal = BrainJournal(db)
    task = "private prompt marker DO_NOT_PERSIST"
    result = journal.record_observation(
        task=task,
        outcome="reported_success",
        reason_code="tests_passed_reported",
        evidence_refs=["sha256:abc123"],
        metrics={"duration_ms": 120, "arbitrary_prompt": 999, "input_tokens": 20},
    )
    assert result["raw_task_stored"] is False and result["verification_claimed"] is False
    assert task.encode() not in db.read_bytes() and b"arbitrary_prompt" not in db.read_bytes()
    summary = journal.summary()
    assert summary["observation_count"] == 1 and summary["outcomes"]["reported_success"] == 1
    assert summary["self_reported_outcomes_are_verified"] is False


def test_improvement_proposals_remain_candidates_until_owner_review(tmp_path):
    journal = BrainJournal(tmp_path / "brain.sqlite3")
    item = journal.propose_improvement(
        candidate_type="retrieval_quality",
        title="Add multilingual semantic retrieval",
        rationale=(
            "Benchmark semantic retrieval against lexical baseline using a rights-cleared corpus."
        ),
        evidence_refs=["evidence:retrieval-benchmark-001"],
    )
    assert (
        item["state"] == "candidate"
        and item["owner_approval_required"] is True
        and item["auto_promotion"] is False
    )
    assert journal.summary()["pending_improvement_candidates"] == 1


def test_journal_rejects_untrusted_outcomes_and_secret_shaped_refs(tmp_path):
    journal = BrainJournal(tmp_path / "brain.sqlite3")
    with pytest.raises(ValueError):
        journal.record_observation(task="task", outcome="verified")
    with pytest.raises(ValueError):
        journal.record_observation(
            task="task", outcome="reported_success", evidence_refs=["ghp_" + "a" * 30]
        )


def test_brain_journal_database_is_private_to_owner(tmp_path):
    import os
    import stat

    db = tmp_path / "brain.sqlite3"
    BrainJournal(db)
    assert stat.S_IMODE(os.stat(db).st_mode) == 0o600


def test_brain_journal_rejects_symlink_without_touching_target(tmp_path):
    target = tmp_path / "target.sqlite3"
    target.write_bytes(b"do not modify")
    link = tmp_path / "brain.sqlite3"
    link.symlink_to(target)

    with pytest.raises(OSError):
        BrainJournal(link)

    assert target.read_bytes() == b"do not modify"


def test_brain_journal_tightens_existing_database_permissions(tmp_path):
    import os
    import stat

    db = tmp_path / "brain.sqlite3"
    BrainJournal(db)
    db.chmod(0o644)

    BrainJournal(db)

    assert stat.S_IMODE(os.stat(db).st_mode) == 0o600


def test_brain_journal_tightens_existing_wal_and_shm_permissions(tmp_path):
    import os
    import stat

    db = tmp_path / "brain.sqlite3"
    journal = BrainJournal(db)
    first = journal._connect()
    first.execute("PRAGMA journal_mode=WAL")
    first.execute("CREATE TABLE IF NOT EXISTS sidecar_probe (value INTEGER)")
    first.execute("INSERT INTO sidecar_probe VALUES (1)")
    wal = Path(f"{db}-wal")
    shm = Path(f"{db}-shm")
    assert wal.exists() and shm.exists()
    wal.chmod(0o644)
    shm.chmod(0o644)

    second = journal._connect()
    try:
        assert stat.S_IMODE(os.stat(wal).st_mode) == 0o600
        assert stat.S_IMODE(os.stat(shm).st_mode) == 0o600
    finally:
        second.close()
        first.close()


def test_brain_journal_rejects_symlinked_wal_sidecar(tmp_path):
    target = tmp_path / "target-wal"
    target.write_bytes(b"do not modify")
    db = tmp_path / "brain.sqlite3"
    Path(f"{db}-wal").symlink_to(target)

    with pytest.raises(OSError):
        BrainJournal(db)

    assert target.read_bytes() == b"do not modify"


def test_brain_journal_creates_new_private_database_parent(tmp_path):
    import os
    import stat

    database = tmp_path / "new-parent" / "private-state" / "brain.sqlite3"
    BrainJournal(database)

    assert stat.S_IMODE(os.stat(database.parent).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(database).st_mode) == 0o600


def test_brain_journal_rejects_existing_world_writable_parent_without_chmod(tmp_path):
    import stat

    parent = tmp_path / "unsafe"
    parent.mkdir()
    parent.chmod(0o777)

    with pytest.raises(PermissionError, match="existing directory permissions"):
        BrainJournal(parent / "brain.sqlite3")

    assert stat.S_IMODE(parent.stat().st_mode) == 0o777
    assert not (parent / "brain.sqlite3").exists()


@pytest.mark.parametrize("attribute", ["geteuid", "O_NOFOLLOW"])
def test_sqlite_security_fails_closed_without_posix_primitives(tmp_path, monkeypatch, attribute):
    from creator_app import sqlite_security

    monkeypatch.delattr(sqlite_security.os, attribute, raising=False)
    with pytest.raises(OSError, match="require POSIX"):
        BrainJournal(tmp_path / "brain.sqlite3")


def test_brain_journal_rejects_fifo_database_path(tmp_path):
    import os

    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO paths are not supported on this platform")
    database = tmp_path / "brain.sqlite3"
    os.mkfifo(database)

    with pytest.raises(OSError, match="regular files"):
        BrainJournal(database)


def test_brain_journal_rejects_hard_link_database_path(tmp_path):
    import os

    target = tmp_path / "shared-data"
    target.write_bytes(b"not a sqlite database")
    database = tmp_path / "brain.sqlite3"
    os.link(target, database)

    with pytest.raises(OSError, match="hard-linked"):
        BrainJournal(database)

    assert target.read_bytes() == b"not a sqlite database"


def test_readonly_sqlite_supports_active_wal_and_wal_without_shm(tmp_path):
    import os
    import shutil
    import stat

    from creator_app.sqlite_security import connect_sqlite_database

    database = tmp_path / "journal.sqlite3"
    journal = BrainJournal(database)
    writer = journal._connect()
    writer.execute("CREATE TABLE IF NOT EXISTS wal_probe (value TEXT)")
    writer.execute("INSERT INTO wal_probe VALUES ('committed-in-wal')")

    reader = connect_sqlite_database(database, timeout=2, readonly=True)
    assert reader.execute("SELECT value FROM wal_probe").fetchone() == ("committed-in-wal",)
    reader.close()

    copied_dir = tmp_path / "wal-copy"
    copied_dir.mkdir(mode=0o700)
    copied_dir.chmod(0o700)
    copied_db = copied_dir / "journal.sqlite3"
    shutil.copy2(database, copied_db)
    shutil.copy2(Path(f"{database}-wal"), Path(f"{copied_db}-wal"))
    assert not Path(f"{copied_db}-shm").exists()

    previous_umask = os.umask(0)
    try:
        copied_reader = connect_sqlite_database(copied_db, timeout=2, readonly=True)
    finally:
        os.umask(previous_umask)
    try:
        assert copied_reader.execute("SELECT value FROM wal_probe").fetchone() == (
            "committed-in-wal",
        )
        assert stat.S_IMODE(os.stat(f"{copied_db}-shm").st_mode) == 0o600
    finally:
        copied_reader.close()
        writer.close()


def test_new_wal_sidecars_are_private_under_permissive_umask(tmp_path):
    import os
    import stat

    database = tmp_path / "brain.sqlite3"
    previous_umask = os.umask(0)
    try:
        journal = BrainJournal(database)
        writer = journal._connect()
        writer.execute("CREATE TABLE IF NOT EXISTS umask_probe (value INTEGER)")
        writer.execute("INSERT INTO umask_probe VALUES (1)")
        wal = Path(f"{database}-wal")
        shm = Path(f"{database}-shm")
        assert wal.exists() and shm.exists()
        assert stat.S_IMODE(os.stat(wal).st_mode) == 0o600
        assert stat.S_IMODE(os.stat(shm).st_mode) == 0o600
        writer.close()
    finally:
        os.umask(previous_umask)


def test_brain_journal_rejects_existing_sticky_shared_directory_without_chmod(tmp_path):
    import stat

    parent = tmp_path / "sticky-shared"
    parent.mkdir()
    parent.chmod(0o1777)

    with pytest.raises(PermissionError, match="existing directory permissions"):
        BrainJournal(parent / "brain.sqlite3")

    assert stat.S_IMODE(parent.stat().st_mode) == 0o1777


def test_brain_journal_rejects_existing_readable_database_directory_without_chmod(tmp_path):
    import stat

    parent = tmp_path / "readable"
    parent.mkdir()
    parent.chmod(0o755)

    with pytest.raises(PermissionError, match="existing directory permissions"):
        BrainJournal(parent / "brain.sqlite3")

    assert stat.S_IMODE(parent.stat().st_mode) == 0o755


@pytest.mark.parametrize("suffix", ["-journal", "-shm"])
def test_sqlite_security_rejects_symlinked_journal_and_shm_sidecars(tmp_path, suffix):
    from creator_app.sqlite_security import connect_sqlite_database

    database = tmp_path / "sidecar-probe.sqlite3"
    database.touch()
    target = tmp_path / "sidecar-target"
    target.write_bytes(b"do not modify")
    Path(f"{database}{suffix}").symlink_to(target)

    with pytest.raises(OSError):
        connect_sqlite_database(database, timeout=1)

    assert target.read_bytes() == b"do not modify"


def test_readonly_sqlite_preserves_explicit_isolation_level(tmp_path):
    from creator_app.sqlite_security import connect_sqlite_database

    database = tmp_path / "readonly-isolation.sqlite3"
    BrainJournal(database)
    connection = connect_sqlite_database(database, timeout=1, readonly=True, isolation_level=None)
    try:
        assert connection.isolation_level is None
    finally:
        connection.close()


def test_connect_sqlite_database_expands_tilde_for_direct_callers(tmp_path, monkeypatch):
    import sqlite3

    from creator_app.sqlite_security import connect_sqlite_database

    home = tmp_path / "home"
    state = home / "state"
    state.mkdir(parents=True, mode=0o700)
    state.chmod(0o700)
    monkeypatch.setenv("HOME", str(home))

    database = state / "direct.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE probe (value TEXT)")
        connection.execute("INSERT INTO probe VALUES ('expanded')")

    database.chmod(0o600)
    connection = connect_sqlite_database("~/state/direct.sqlite3", timeout=1, readonly=True)
    try:
        assert connection.execute("SELECT value FROM probe").fetchone() == ("expanded",)
    finally:
        connection.close()


def test_sqlite_security_detects_database_path_swap_during_connect(tmp_path, monkeypatch):
    import sqlite3

    from creator_app import sqlite_security

    database = tmp_path / "race-probe.sqlite3"
    database.touch()
    target = tmp_path / "replacement.sqlite3"
    target_connection = sqlite3.connect(target)
    target_connection.execute("CREATE TABLE sentinel (value TEXT)")
    target_connection.execute("INSERT INTO sentinel VALUES ('unchanged')")
    target_connection.commit()
    target_connection.close()
    target_before = target.read_bytes()
    real_connect = sqlite3.connect

    def replace_path_then_connect(path, *args, **kwargs):
        assert Path(path) == database
        database.unlink()
        database.symlink_to(target)
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(sqlite_security.sqlite3, "connect", replace_path_then_connect)

    with pytest.raises(OSError, match="path changed while connecting"):
        sqlite_security.connect_sqlite_database(database, timeout=1)

    assert target.read_bytes() == target_before


def test_sqlite_database_path_disappearing_during_connect_fails_closed(tmp_path, monkeypatch):
    import sqlite3

    from creator_app.sqlite_security import connect_sqlite_database

    database = tmp_path / "disappearing.sqlite3"
    original_connect = sqlite3.connect

    def connect_then_unlink(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        database.unlink()
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect_then_unlink)
    with pytest.raises(OSError, match="database path disappeared"):
        connect_sqlite_database(database, timeout=1)


def test_brain_runtime_expands_tilde_journal_path_consistently(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    brain = BrainRuntime(
        root=_root(tmp_path),
        journal_path="~/state/brain.sqlite3",
        task_db_path=tmp_path / "tasks.sqlite3",
        knowledge_db_path=tmp_path / "missing.sqlite3",
        evidence_dir=tmp_path / "missing-evidence",
    )

    brain.record_observation(task="tilde-path", outcome="reported_success")

    assert brain.journal_path == home / "state" / "brain.sqlite3"
    assert brain.journal_path.is_file()
    assert brain.journal_summary()["observation_count"] == 1
