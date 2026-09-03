from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: prepare_docker_probe_v2.py OUTPUT")
        return 2

    source = Path("scripts/docker_capability_probe.py").read_text(encoding="utf-8")

    old_secret_check = 'if "sk-" in serialized or "private_key" in serialized:\n                raise RuntimeError("credential material pattern appeared in status output")'
    new_secret_check = 'if "sk-" in serialized or self.token.lower() in serialized or (\n                self.webhook_token and self.webhook_token.lower() in serialized\n            ):\n                raise RuntimeError("actual test credential material appeared in status output")'

    old_provider = '"provider": "docker-probe",'
    new_provider = '"provider": "gmail",'

    if source.count(old_secret_check) != 1:
        raise RuntimeError("expected one credential-check patch target")
    if source.count(old_provider) != 1:
        raise RuntimeError("expected one email-provider patch target")

    source = source.replace(old_secret_check, new_secret_check)
    source = source.replace(old_provider, new_provider)

    output = Path(sys.argv[1])
    output.write_text(source, encoding="utf-8")
    print(f"wrote corrected probe: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
