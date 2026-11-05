from __future__ import annotations

import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "ops/vps/services/cknexus_scanner_api.py"


@pytest.fixture
def scanner_api(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("cknexus_scanner_api_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    token_file = tmp_path / "token"
    token_file.write_text("test-token", encoding="utf-8")
    monkeypatch.setattr(module, "R", workspace)
    monkeypatch.setattr(module, "T", token_file)
    monkeypatch.setattr(module, "E", evidence)

    server = ThreadingHTTPServer(("127.0.0.1", 0), module.H)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield module, f"http://127.0.0.1:{server.server_port}/api/scan"
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def post(url: str, token: str, payload: object) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.mark.parametrize(
    "target",
    [
        "/opt/actions-runner/_work/ck-nexus/ck-nexus/../../etc",
        "",
        None,
        123,
        ["not", "a", "path"],
        {"path": "/tmp"},
    ],
)
def test_scan_endpoint_rejects_noncanonical_and_nonstring_targets(
    scanner_api, monkeypatch, target
):
    module, url = scanner_api

    def unexpected_scan(*args, **kwargs):
        raise AssertionError("scanner must not run for a rejected target")

    monkeypatch.setattr(module.subprocess, "run", unexpected_scan)
    status, body = post(url, "test-token", {"target": target, "scanners": ["trivy"]})

    assert status == 400
    assert body == {"error": "target_not_allowed"}


def test_scan_endpoint_accepts_exact_canonical_target(scanner_api, monkeypatch):
    module, url = scanner_api

    def fake_scan(args, **kwargs):
        output_path = Path(args[args.index("--output") + 1])
        output_path.write_text(json.dumps({"Results": []}), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_scan)
    status, body = post(
        url,
        "test-token",
        {"target": str(module.R), "scanners": ["trivy"]},
    )

    assert status == 200
    assert body["status"] == "EXECUTED_NOT_VERIFIED"
    assert body["summary"]["trivy"]["exit_code"] == 0
    assert (module.E / f"{body['scan_id']}.json").is_file()
