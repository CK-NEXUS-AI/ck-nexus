import json
import os
import subprocess
import sys

if not os.getenv("CKNEXUS_ALERT_RECEIPT_FILE"):
    print(
        json.dumps(
            {
                "status": "BLOCKED",
                "reason": (
                    "Set CKNEXUS_ALERT_RECEIPT_FILE to captured operator alert evidence "
                    "after failure injection."
                ),
            }
        )
    )
    raise SystemExit(2)
p = subprocess.run([sys.executable, "scripts/p0_observability_check.py"], text=True)
raise SystemExit(p.returncode)
