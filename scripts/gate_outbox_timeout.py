import json
import os

if not os.getenv("CKNEXUS_PROVIDER_TIMEOUT_TEST_URL"):
    print(
        json.dumps(
            {
                "status": "BLOCKED",
                "reason": (
                    "Set CKNEXUS_PROVIDER_TIMEOUT_TEST_URL to a staging provider/fault-injection "
                    "endpoint that can prove accept+timeout+retry semantics."
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
                "Provider-specific timeout harness must be configured for the selected "
                "SMTP/API provider before this gate can PASS."
            ),
        }
    )
)
raise SystemExit(2)
