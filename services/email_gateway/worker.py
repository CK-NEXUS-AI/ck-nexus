from __future__ import annotations

import argparse
import os
import socket
import time
from pathlib import Path

from services.email_gateway.factory import create_email_repository
from services.email_gateway.repository import OutboxItem


def placeholder_sender(item: OutboxItem) -> str:
    """No network side effect by default.

    Production must inject a provider-specific sender. This worker refuses to
    pretend that delivery happened merely because an outbox row exists.
    """
    raise RuntimeError(
        f"No production sender configured for action={item.action_type!r}, "
        f"destination={item.destination!r}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="CK-NEXUS email outbox worker")
    parser.add_argument(
        "--database", default=os.getenv("CKNEXUS_EMAIL_DATABASE_PATH", "data/cknexus.db")
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    repository = create_email_repository(
        database_url=os.getenv("CKNEXUS_EMAIL_DATABASE_URL", ""),
        database_path=Path(args.database),
    )
    repository.initialize()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"

    while True:
        repository.recover_expired_leases()
        result = repository.run_outbox_once(worker_id=worker_id, sender=placeholder_sender)
        print(result, flush=True)
        if args.once:
            return 0
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
