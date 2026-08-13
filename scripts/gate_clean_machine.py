import json
import os

if os.getenv("CKNEXUS_CLEAN_MACHINE") != "YES":
    print(
        json.dumps(
            {
                "status": "BLOCKED",
                "reason": "Run this gate on a fresh VM/host with CKNEXUS_CLEAN_MACHINE=YES; same-host reruns are not clean-machine evidence.",
            }
        )
    )
    raise SystemExit(2)
print(
    json.dumps(
        {
            "status": "BLOCKED",
            "reason": "Fresh-host installer evidence collector is deployment-specific; record install/start/smoke logs and duration before PASS.",
        }
    )
)
raise SystemExit(2)
