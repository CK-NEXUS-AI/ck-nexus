from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import tempfile
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.email_gateway.factory import create_email_repository


def main() -> int:
    parser = argparse.ArgumentParser(description="P0-EMAIL-001 duplicate concurrency proof")
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--attempts", type=int, default=100)
    parser.add_argument("--database")
    parser.add_argument(
        "--database-url",
        default=os.getenv("CKNEXUS_EMAIL_DATABASE_URL", "").strip(),
        help="PostgreSQL URL; defaults to CKNEXUS_EMAIL_DATABASE_URL",
    )
    parser.add_argument(
        "--require-postgres",
        action="store_true",
        help="Exit BLOCKED (2) unless a PostgreSQL URL is configured.",
    )
    args = parser.parse_args()

    database_url = (args.database_url or "").strip()
    is_postgres = database_url.startswith(("postgresql://", "postgres://"))
    if args.require_postgres and not is_postgres:
        print("P0-EMAIL-001 BLOCKED: PostgreSQL URL is required")
        return 2

    temp = None
    if is_postgres:
        database = Path("unused-postgres-path.db")
    elif args.database:
        database = Path(args.database)
    else:
        temp = tempfile.TemporaryDirectory(prefix="ckn-email-gate-")
        database = Path(temp.name) / "email-gateway.db"

    try:
        repo = create_email_repository(database_url=database_url, database_path=database)
        repo.initialize()
    except (RuntimeError, OSError, ValueError) as exc:
        label = "BLOCKED" if args.require_postgres else "FAIL"
        print(f"P0-EMAIL-001 {label}: repository unavailable: {type(exc).__name__}: {exc}")
        return 2 if args.require_postgres else 1

    run_id = uuid.uuid4().hex
    mailbox = "admin@ck-nexus.test"
    provider = "gmail"
    provider_message_id = f"p0-concurrency-{run_id}"
    internet_message_id = f"<{provider_message_id}@example.test>"

    def attempt(index: int) -> bool:
        result = repo.claim_message(
            mailbox=mailbox,
            provider=provider,
            provider_message_id=provider_message_id,
            internet_message_id=internet_message_id,
            claimed_by=f"concurrency-{index}",
            lease_seconds=300,
        )
        return result.claimed

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            claimed = list(pool.map(attempt, range(max(1, args.attempts))))
        winners = sum(claimed)
        rows = repo.count_journal_message(
            mailbox=mailbox,
            provider=provider,
            provider_message_id=provider_message_id,
        )
    except Exception as exc:
        print(f"P0-EMAIL-001 FAIL: concurrency execution error: {type(exc).__name__}: {exc}")
        return 1
    finally:
        if temp is not None:
            temp.cleanup()

    backend = "postgresql" if is_postgres else "sqlite"
    print(
        f"backend={backend} attempts={max(1, args.attempts)} "
        f"winners={winners} matching_journal_rows={rows}"
    )
    if winners != 1 or rows != 1:
        print("P0-EMAIL-001 FAIL")
        return 1
    if is_postgres:
        print("P0-EMAIL-001 POSTGRESQL CONCURRENCY PASS")
    else:
        print("P0-EMAIL-001 LOCAL SQLITE CONCURRENCY PASS (non-production evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
