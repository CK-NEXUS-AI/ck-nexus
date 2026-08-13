import json
import os

if not os.getenv("CKNEXUS_END_TO_END_TRACE_ID"):
    print(
        json.dumps(
            {
                "status": "BLOCKED",
                "reason": (
                    "Set CKNEXUS_END_TO_END_TRACE_ID after driving one real message "
                    "ingress→CK-NEXUS router→outbox→provider; gate requires complete "
                    "correlated runtime trace."
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
                "A trace ID alone is insufficient; the staging evidence collector must verify "
                "all required lifecycle events before PASS."
            ),
        }
    )
)
raise SystemExit(2)
