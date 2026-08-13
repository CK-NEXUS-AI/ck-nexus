from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = {
    ROOT / "creator_app" / "runtime_binding.py": ("verify_runtime_binding_or_raise", "runtime_binding_status"),
    ROOT / "deploy" / "Caddyfile": ("Strict-Transport-Security", "reverse_proxy app:8000", "max_size 2MB"),
    ROOT / "docker-compose.prod.yml": ("CKNEXUS_RUNTIME_BINDING_ENABLED", "DATABASE_URL", "REDIS_URL", "edge:"),
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

compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
if '"80:80"' not in compose or '"443:443"' not in compose:
    errors.append("edge-ports-not-exposed")
if '127.0.0.1:${CKNEXUS_PORT:-8000}:8000' in compose:
    errors.append("app-port-still-host-exposed")

if errors:
    print("R26_RUNTIME_TLS_GATE=FAIL")
    for item in errors:
        print(item)
    raise SystemExit(1)

print("R26_RUNTIME_TLS_GATE=PASS")
