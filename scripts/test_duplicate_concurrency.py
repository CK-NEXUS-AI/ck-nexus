from __future__ import annotations

import argparse
import concurrent.futures
import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.email_gateway.repository import EmailGatewayRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="P0-EMAIL-001 duplicate concurrency proof")
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--attempts", type=int, default=100)
    parser.add_argument("--database")
    args = parser.parse_args()

    temp = None
    if args.database:
        database = Path(args.database)
    else:
        temp = tempfile.TemporaryDirectory(prefix="ckn-email-gate-")
        database = Path(temp.name) / "email-gateway.db"

    repo = EmailGatewayRepository(database)
    repo.initialize()

    def attempt(index: int) -> bool:
        result = repo.claim_message(
            mailbox="admin@ck-nexus.test",
            provider="gmail",
            provider_message_id="provider-msg-001",
            internet_message_id="<internet-msg-001@example.test>",
            claimed_by=f"concurrency-{index}",
            lease_seconds=300,
        )
        return result.claimed

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        claimed = list(pool.map(attempt, range(max(1, args.attempts))))

    winners = sum(claimed)
    rows = repo.count_journal()
    print(f"attempts={args.attempts} winners={winners} journal_rows={rows}")
    if winners != 1 or rows != 1:
        print("P0-EMAIL-001 FAIL")
        return 1
    print("P0-EMAIL-001 LOCAL SQLITE CONCURRENCY PASS")
    if temp is not None:
        temp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
