from __future__ import annotations

import concurrent.futures
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMES: dict[str, float] = {}
RESULTS: dict[str, dict] = {}


def run_thread(name, fn):
    started = time.perf_counter()
    result = fn()
    TIMES[name] = round(time.perf_counter() - started, 4)
    RESULTS[name] = {"status": "PASS", "result": result, "seconds": TIMES[name]}
    return RESULTS[name]


def core_fixer():
    identity = ROOT / "creator_app/council_authority/identity.py"
    source = identity.read_text()
    if "def verify_token(token: str) -> CallerIdentity:" not in source:
        source = source.replace("import json\n", "import json\nimport os\n", 1)
        source += '''

def verify_token(token: str) -> CallerIdentity:
    """Verify an approver token using the configured Core/L3 identity secret.

    Missing or weak secrets fail closed; no development fallback is accepted.
    Only identities carrying the authority's admin role may approve task completion.
    """
    secret = os.environ.get("CK_IDENTITY_SECRET")
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise IdentityError("CK_IDENTITY_SECRET is missing or too short")
    if not isinstance(token, str) or not token:
        raise IdentityError("approver token is required")
    try:
        identity = IdentityVerifier(secret.encode("utf-8")).verify(token)
    except IdentityError:
        raise
    except Exception as exc:
        raise IdentityError("invalid approver token") from exc
    if identity.role != "admin":
        raise IdentityError("approver identity must have admin role")
    if not identity.agent_id.strip() or not identity.service_id.strip():
        raise IdentityError("approver identity claims are incomplete")
    return identity
'''
        identity.write_text(source)

    path = ROOT / "creator_app/control_plane/task_store.py"
    source = path.read_text()
    if "from creator_app.council_authority.identity import verify_token" not in source:
        source = source.replace(
            "from typing import Any\n",
            "from typing import Any\n\n"
            "from creator_app.council_authority.identity import verify_token\n",
            1,
        )
    source = source.replace("approver_id: str | None = None,", "approver_token: str | None = None,")
    old = """        if success and (
            not isinstance(evidence_reference, str)
            or not evidence_reference.strip()
            or not isinstance(approver_id, str)
            or not approver_id.strip()
        ):
            raise ValueError(
                "successful finish requires evidence_reference and approver_id"
            )
        state = "completed" if success else "failed"
        stored_result = dict(result or {})
        if success:
            stored_result["evidence_reference"] = evidence_reference.strip()
            stored_result["approver_id"] = approver_id.strip()
"""
    new = """        approver = None
        if success:
            if not isinstance(evidence_reference, str) or not evidence_reference.strip():
                raise ValueError("successful finish requires evidence_reference")
            if not isinstance(approver_token, str) or not approver_token.strip():
                raise PermissionError("successful finish requires a valid approver token")
            approver = verify_token(approver_token.strip())
        state = "completed" if success else "failed"
        stored_result = dict(result or {})
        if success:
            stored_result["evidence_reference"] = evidence_reference.strip()
            stored_result["approver_id"] = approver.agent_id
            stored_result["approver_service_id"] = approver.service_id
            stored_result["approver_role"] = approver.role
"""
    if old in source:
        source = source.replace(old, new, 1)
    elif (
        "approver_token: str | None = None" not in source
        or 'stored_result["approver_id"] = approver.agent_id' not in source
    ):
        raise RuntimeError("TaskStore.finish contract did not match expected source")
    path.write_text(source)
    return {"changed": [str(identity.relative_to(ROOT)), str(path.relative_to(ROOT))]}


def worker_fixer():
    path = ROOT / "creator_app/control_plane/worker.py"
    source = path.read_text()
    source = source.replace(
        'approver_id=output.get("approver_id"),', 'approver_token=output.get("approver_token"),'
    )
    source = source.replace(
        "            except ValueError as exc:\n                return self._fail(",
        "            except (ValueError, PermissionError) as exc:\n"
        "                return self._fail(",
        1,
    )
    path.write_text(source)

    mcp = ROOT / "creator_app/agnes/mcp_server.py"
    text = mcp.read_text()
    text = text.replace(
        "    approver_id: str | None = None,", "    approver_token: str | None = None,"
    )
    text = text.replace(
        "            approver_id=approver_id,", "            approver_token=approver_token,"
    )
    old = """    except ValueError as exc:
        code = "LEASE_CONFLICT" if "valid lease" in str(exc) else "INVALID_INPUT"
        return _task_result_error(code, str(exc))
    return {
        "ok": True,
        "job_id": job_id,
        "state": "completed" if success else "failed",
"""
    new = """    except PermissionError:
        return _task_result_error("UNAUTHORIZED", "a valid Core/L3 approver token is required")
    except ValueError as exc:
        code = "LEASE_CONFLICT" if "valid lease" in str(exc) else "INVALID_INPUT"
        return _task_result_error(code, str(exc))
    return {
        "ok": True,
        "job_id": job_id,
        "state": "completed" if success else "failed",
"""
    if old in text:
        text = text.replace(old, new, 1)
    mcp.write_text(text)

    auto = ROOT / "creator_app/n8n_intelligence/auto_developer.py"
    atext = auto.read_text().replace(
        "        except ValueError:\n            # Verification evidence is not approval.",
        "        except (ValueError, PermissionError):\n"
        "            # Verification evidence is not approval.",
        1,
    )
    auto.write_text(atext)
    return {
        "changed": [
            str(path.relative_to(ROOT)),
            str(mcp.relative_to(ROOT)),
            str(auto.relative_to(ROOT)),
        ]
    }


def test_writer():
    secret = "test_secret_key_must_be_at_least_32_bytes_long_ok"
    # TaskStore tests
    p = ROOT / "tests/test_control_plane_task_store.py"
    s = p.read_text()
    s = s.replace("import json\n", "import json\nimport os\n", 1)
    s = s.replace(
        "from creator_app.control_plane.task_store import TaskStore\n",
        "from creator_app.control_plane.task_store import TaskStore\n"
        "from creator_app.council_authority.identity import IdentityVerifier\n",
        1,
    )
    helper = f"""

_TEST_SECRET = {secret!r}
os.environ.setdefault("CK_IDENTITY_SECRET", _TEST_SECRET)


def _test_approver_token():
    return IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="test-authority", agent_id="test-approver", role="admin"
    )
"""
    if "def _test_approver_token()" not in s:
        s = s.replace(
            "\n\ndef test_task_store_persists_checkpoint_and_result",
            helper + "\n\ndef test_task_store_persists_checkpoint_and_result",
            1,
        )
    s = s.replace('approver_id="test-approver"', "approver_token=_test_approver_token()")
    p.write_text(s)

    # Worker tests
    p = ROOT / "tests/test_control_plane_worker.py"
    s = p.read_text()
    s = s.replace("import time\n", "import time\nimport os\n", 1)
    s = s.replace(
        "from creator_app.control_plane.task_store import TaskStore\n",
        "from creator_app.control_plane.task_store import TaskStore\n"
        "from creator_app.council_authority.identity import IdentityVerifier\n",
        1,
    )
    if "def _test_approver_token()" not in s:
        s = s.replace(
            "\n\ndef test_worker_executes_verifies_and_finishes",
            helper + "\n\ndef test_worker_executes_verifies_and_finishes",
            1,
        )
    s = s.replace('"approver_id": "test-approver"', '"approver_token": _test_approver_token()')
    p.write_text(s)

    # MCP tests
    p = ROOT / "tests/test_control_plane_mcp.py"
    s = p.read_text()
    s = s.replace("import pytest\n", "import os\n\nimport pytest\n", 1)
    s = s.replace(
        "import creator_app.agnes.mcp_server as mcp_server\n",
        "import creator_app.agnes.mcp_server as mcp_server\n"
        "from creator_app.council_authority.identity import IdentityVerifier\n",
        1,
    )
    if "def _test_approver_token()" not in s:
        s = s.replace(
            "\n\ndef test_auto_dispatch_development_exposes_control_plane_graph",
            helper + "\n\ndef test_auto_dispatch_development_exposes_control_plane_graph",
            1,
        )
    s = s.replace('approver_id="test-approver"', "approver_token=_test_approver_token()")
    s = s.replace(
        'assert rejected["error_code"] == "INVALID_INPUT"',
        'assert rejected["error_code"] == "UNAUTHORIZED"',
    )
    p.write_text(s)

    # Existing proactive tests
    p = ROOT / "tests/test_n8n_proactive.py"
    s = p.read_text()
    s = s.replace("import json\n", "import json\nimport os\n", 1)
    s = s.replace(
        "from creator_app.control_plane.task_store import TaskStore\n",
        "from creator_app.control_plane.task_store import TaskStore\n"
        "from creator_app.council_authority.identity import IdentityVerifier\n",
        1,
    )
    if "def _test_approver_token()" not in s:
        s = s.replace("\n\ndef ", helper + "\n\ndef ", 1)
    s = s.replace('approver_id="test-approver"', "approver_token=_test_approver_token()")
    p.write_text(s)

    # P0 focused regression suite
    p = ROOT / "tests/p0_repro_test.py"
    s = p.read_text()
    s = s.replace("import pytest\n", "import os\n\nimport pytest\n", 1)
    s = s.replace(
        "from creator_app.control_plane.task_store import TaskStore\n",
        "from creator_app.control_plane.task_store import TaskStore\n"
        "from creator_app.council_authority.identity import IdentityVerifier\n",
        1,
    )
    if "def _test_approver_token()" not in s:
        s = s.replace("\n\nclass AlwaysVerified:", helper + "\n\nclass AlwaysVerified:", 1)
    s = s.replace(
        "test_b_finish_success_requires_evidence_reference_and_approver_id",
        "test_b_finish_success_requires_evidence_reference_and_approver_token",
    )
    s = s.replace(
        'with pytest.raises(ValueError, match="evidence_reference.*approver_id"):',
        'with pytest.raises(PermissionError, match="approver token"):',
    )
    s = s.replace(
        'approver_id="untrusted-arbitrary-string"', 'approver_token="untrusted-arbitrary-string"'
    )
    s += """

def test_d_finish_accepts_valid_approver_token(tmp_path):
    store = TaskStore(tmp_path / "valid-approver.sqlite3")
    store.enqueue("p0-valid-approver", {"description": "valid approver reproduction"})
    claimed = store.claim_next("trusted-worker", lease_seconds=60)
    assert claimed is not None
    token = IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="core-l3-test", agent_id="authorized-owner", role="admin"
    )

    store.finish(
        "p0-valid-approver",
        success=True,
        result={"passed": True},
        evidence_reference="evidence://verified-test-fixture",
        approver_token=token,
        worker_id="trusted-worker",
        lease_token=claimed["lease_token"],
    )
    completed = store.get("p0-valid-approver")
    assert completed is not None
    assert completed["state"] == "completed"
    import json
    stored = json.loads(completed["result_json"])
    assert stored["approver_id"] == "authorized-owner"
    assert stored["approver_role"] == "admin"


def test_e_finish_rejects_valid_non_admin_token(tmp_path):
    store = TaskStore(tmp_path / "non-admin.sqlite3")
    store.enqueue("p0-non-admin", {"description": "non-admin must not approve"})
    claimed = store.claim_next("worker", lease_seconds=60)
    assert claimed is not None
    token = IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="worker-service", agent_id="ordinary-agent", role="agent"
    )
    with pytest.raises(PermissionError, match="admin role"):
        store.finish(
            "p0-non-admin",
            success=True,
            result={},
            evidence_reference="evidence://test",
            approver_token=token,
            worker_id="worker",
            lease_token=claimed["lease_token"],
        )
"""
    p.write_text(s)
    return {
        "changed": [
            "tests/test_control_plane_task_store.py",
            "tests/test_control_plane_worker.py",
            "tests/test_control_plane_mcp.py",
            "tests/test_n8n_proactive.py",
            "tests/p0_repro_test.py",
        ]
    }


def env_scanner():
    usage = shutil.disk_usage(ROOT)
    try:
        import psutil

        ram = {
            "available": psutil.virtual_memory().available,
            "total": psutil.virtual_memory().total,
        }
    except Exception:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            info[k] = int(v.strip().split()[0]) * 1024
        ram = {"available": info["MemAvailable"], "total": info["MemTotal"]}
    return {
        "disk_total": usage.total,
        "disk_free": usage.free,
        "disk_used_percent": round((usage.total - usage.free) / usage.total * 100, 2),
        "ram": ram,
        "python": sys.version,
        "python_executable": sys.executable,
        "pytest": subprocess.check_output(
            [sys.executable, "-m", "pytest", "--version"], text=True
        ).strip(),
    }


def main():
    started = time.perf_counter()
    jobs = {
        "Core-Fixer": core_fixer,
        "Worker-Fixer": worker_fixer,
        "Test-Writer": test_writer,
        "Env-Scanner": env_scanner,
    }
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="cknexus-p0"
    ) as pool:
        futures = {pool.submit(run_thread, name, fn): name for name, fn in jobs.items()}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as exc:
                RESULTS[name] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    report = {
        "threads": RESULTS,
        "total_seconds": round(time.perf_counter() - started, 4),
        "max_workers": 4,
        "all_threads_passed": all(x.get("status") == "PASS" for x in RESULTS.values()),
    }
    out = ROOT / "scripts/fast_swarm_result.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["all_threads_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
