#!/usr/bin/env python3
"""Safe Gmail OAuth setup helper for CK-NEXUS.

This helper deliberately does **not** exchange authorization codes, print
access/refresh tokens, or write credential values into ``.env``. CK-NEXUS
already has a server-side OAuth flow backed by the Credential Broker.

Use the canonical application endpoints instead:
- GET /api/integrations/gmail/status
- GET /api/integrations/gmail/oauth/start
- GET /api/integrations/gmail/oauth/callback
- POST /api/integrations/gmail/revoke-local
"""

from __future__ import annotations

import os

_REQUIRED_ENV_NAMES = (
    "CKNEXUS_GMAIL_OAUTH_ENABLED",
    "GMAIL_CLIENT_ID",
    "GMAIL_CLIENT_SECRET",
    "GMAIL_REDIRECT_URI",
)


def _configured(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def main() -> int:
    """Print redacted setup state and the governed OAuth route to use."""
    configured = {name: _configured(name) for name in _REQUIRED_ENV_NAMES}

    print("CK-NEXUS Gmail OAuth setup")
    print("============================")
    for name, present in configured.items():
        print(f"{name}: {'configured' if present else 'missing'}")

    print()
    print("No token or secret value is displayed by this helper.")
    print("Start CK-NEXUS, authenticate to its local API, then call:")
    print("  GET /api/integrations/gmail/oauth/start")
    print("Open the returned Google authorization URL in your browser.")
    print("Google redirects to the configured GMAIL_REDIRECT_URI; CK-NEXUS")
    print("exchanges the one-time code server-side and stores tokens through")
    print("the Credential Broker / encrypted vault when configured.")

    return 0 if all(configured.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
