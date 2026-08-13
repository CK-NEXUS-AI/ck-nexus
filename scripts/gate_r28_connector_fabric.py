from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = {
    ROOT / "creator_app" / "connector_fabric" / "mcp.py": (
        "2026-07-28",
        "server/discover",
        "Mcp-Method",
    ),
    ROOT / "creator_app" / "connector_fabric" / "security.py": (
        "Credentials are not allowed",
        "non-public address",
        "x-mcp-header",
    ),
    ROOT / "creator_app" / "connector_fabric" / "fabric.py": (
        "FailClosedAuthorizer",
        "ACTIVE_READ_ONLY",
        "execution_denied",
    ),
    ROOT / "creator_app" / "connector_fabric" / "evidence.py": ("previousHash", "entryHash"),
    ROOT / "creator_app" / "api.py": ("/api/connectors", "CONNECTOR_DISCOVERY_BLOCKED"),
    ROOT / "tests" / "test_r28_connector_fabric.py": (
        "test_mcp_2026_discovery_paginates",
        "fail_closed_execution",
    ),
}

errors: list[str] = []
for path, markers in required.items():
    if not path.is_file():
        errors.append(f"missing:{path.relative_to(ROOT)}")
        continue
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            errors.append(f"missing-marker:{path.relative_to(ROOT)}:{marker}")

api_text = (ROOT / "creator_app" / "api.py").read_text(encoding="utf-8")
if "/api/connectors/{connector_id}/execute" in api_text:
    errors.append("unsafe-public-execution-endpoint-present")

if errors:
    print("R28_CONNECTOR_FABRIC_GATE=FAIL")
    for item in errors:
        print(item)
    raise SystemExit(1)

print("R28_CONNECTOR_FABRIC_GATE=PASS")
