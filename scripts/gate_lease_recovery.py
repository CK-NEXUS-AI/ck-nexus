import json
import os

if os.getenv("CKNEXUS_ALLOW_WORKER_SIGKILL_TEST") != "YES":
    print(
        json.dumps(
            {
                "status": "BLOCKED",
                "reason": (
                    "Set CKNEXUS_ALLOW_WORKER_SIGKILL_TEST=YES in isolated staging and "
                    "configure the worker supervisor before destructive worker-kill evidence."
                ),
            }
        )
    )
    raise SystemExit(2)
print(
    json.dumps(
        {
            "status": "BLOCKED",
            "reason": (
                "Worker supervisor/kill target is deployment-specific; attach SIGKILL + "
                "reclaim evidence through the staging harness."
            ),
        }
    )
)
raise SystemExit(2)
