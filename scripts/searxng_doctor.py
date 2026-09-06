from __future__ import annotations

import argparse
import json

from creator_app.global_knowledge.searxng_runtime import check_json_api


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8080/",
    )
    parser.add_argument(
        "--query",
        default="ck nexus",
    )
    args = parser.parse_args()

    result = check_json_api(
        args.base_url,
        query=args.query,
    )
    print(
        json.dumps(
            {
                "ok": result.ok,
                "reason": result.reason,
                "result_count": result.result_count,
            },
            sort_keys=True,
        )
    )
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
