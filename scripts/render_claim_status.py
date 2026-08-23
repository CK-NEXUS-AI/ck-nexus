from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_claim_registry import publication_status, validate_claim


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("claim", type=Path)
    parser.add_argument("--current-subject-commit")
    args = parser.parse_args()

    with args.claim.open(encoding="utf-8") as handle:
        claim = json.load(handle)
    errors = validate_claim(claim)
    if errors:
        raise SystemExit("; ".join(errors))

    status = publication_status(claim, args.current_subject_commit)
    output = {
        "claim_id": claim["claim_id"],
        "claim_text_th": claim["claim_text_th"],
        "state": claim["state"],
        "publication_status": status,
        "subject_commit": claim["subject"]["commit"],
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
