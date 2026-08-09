from __future__ import annotations

import json
from pathlib import Path

RULES = Path(__file__).resolve().parents[1] / "observability" / "alert_rules.yaml"
REQUIRED = ("CKNexusHigh5xxRate", "CKNexusEmailStaleLeases", "CKNexusEmailOutboxBacklog")

def main() -> int:
    text = RULES.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED if name not in text]
    status = "PASS" if not missing else "FAIL"
    print(json.dumps({"status": status, "rules": list(REQUIRED), "missing": missing}, sort_keys=True))
    return 0 if not missing else 1

if __name__ == "__main__":
    raise SystemExit(main())
