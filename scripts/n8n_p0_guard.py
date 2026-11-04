from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def is_n8n_workflow(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("nodes"), list)
        and isinstance(value.get("connections"), dict)
    )


def inspect_workflow(workflow: dict[str, Any], source: str = "<memory>") -> list[str]:
    findings: list[str] = []
    for node in workflow.get("nodes", []):
        if not isinstance(node, dict):
            continue
        name = str(node.get("name") or "<unnamed>")
        node_type = str(node.get("type") or "")
        params = node.get("parameters")
        if not isinstance(params, dict):
            params = {}

        if node_type.endswith(".webhook"):
            auth = params.get("authentication")
            if not isinstance(auth, str) or auth.lower() in {"", "none"}:
                findings.append(
                    f"{source}: webhook node '{name}' has no configured authentication"
                )

        if node_type.endswith(".httpRequest"):
            url = params.get("url")
            if isinstance(url, str) and url.lower().startswith("http://"):
                host = urlparse(url).hostname or ""
                if host not in {"localhost", "127.0.0.1", "::1"}:
                    findings.append(
                        f"{source}: HTTP request node '{name}' uses non-local cleartext HTTP"
                    )

            header_config = params.get("headerParameters")
            if not isinstance(header_config, dict):
                header_config = {}
            headers = header_config.get("parameters", [])
            if isinstance(headers, list):
                for header in headers:
                    if not isinstance(header, dict):
                        continue
                    header_name = str(header.get("name") or "").strip().lower()
                    header_value = header.get("value")
                    if header_name == "authorization" and isinstance(header_value, str):
                        value = header_value.strip()
                        # Credential expressions are references; literal bearer strings are not.
                        if (
                            value.lower().startswith("bearer ")
                            and "{{" not in value
                            and "$credentials" not in value
                        ):
                            findings.append(
                                f"{source}: HTTP request node '{name}' has a literal "
                                "bearer authorization value"
                            )
    return findings


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(item.decode()) for item in out.split(b"\0") if item]


def main() -> int:
    workflow_count = 0
    findings: list[str] = []
    for path in tracked_files():
        if path.suffix.lower() != ".json" or not path.is_file():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError, json.JSONDecodeError):
            continue
        if is_n8n_workflow(document):
            workflow_count += 1
            findings.extend(inspect_workflow(document, str(path)))

    if findings:
        print("N8N P0 EXPORT GUARD: FAIL")
        print("\n".join(findings))
        return 1
    if workflow_count == 0:
        print(
            "N8N P0 EXPORT GUARD: NOT_APPLICABLE "
            "(no tracked n8n workflow exports; live workflow configuration is not verified)"
        )
        return 0
    print(f"N8N P0 EXPORT GUARD: PASS ({workflow_count} tracked workflow exports checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
