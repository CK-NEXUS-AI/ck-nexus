#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "_inventory"

EXTERNAL_PACK = [
    ("cknexus_security_monitor.ts", "Gmail security monitor / scheduled alert watcher", [
        "creator_app/gmail_oauth.py",
        "services/email_gateway/",
        "creator_app/integration_security.py",
        "creator_app/observability.py",
        "observability/alert_rules.yaml",
    ]),
    ("cknexus_brain_upgrade.ts", "Brain upgrade engine / scheduled cognition maintenance", [
        "creator_app/openai_brain.py",
        "creator_app/provider_router.py",
        "creator_app/providers.py",
        "creator_app/agnes_runtime.py",
        "creator_app/dev_team.py",
    ]),
    ("auto_token_manager.ts", "Connector token lifecycle manager", [
        "creator_app/credential_broker.py",
        "creator_app/credential_vault.py",
        "creator_app/agnes/execution/credentials.py",
    ]),
    ("auto_token_manager.py", "Connector token lifecycle manager", [
        "creator_app/credential_broker.py",
        "creator_app/credential_vault.py",
        "creator_app/agnes/execution/credentials.py",
    ]),
    ("connect_all_plugins.ts", "Connector/plugin bootstrap", [
        "creator_app/connector_fabric/",
        "creator_app/integrations.py",
        "creator_app/integration_security.py",
    ]),
    ("auto_api_wix.ts", "Wix/API connector bootstrap", [
        "creator_app/connector_fabric/openapi.py",
        "creator_app/connector_fabric/registry.py",
        "creator_app/connector_fabric/governance.py",
    ]),
    ("connector_hub.py", "Legacy connector hub", [
        "creator_app/connector_fabric/fabric.py",
        "creator_app/connector_fabric/registry.py",
        "creator_app/integrations.py",
    ]),
    ("post_connect_all.py", "Post-connect activation/verification", [
        "creator_app/connector_fabric/evidence.py",
        "creator_app/connector_fabric/security.py",
        "creator_app/connector_fabric/governance.py",
    ]),
]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(p.decode()) for p in raw.split(b"\0") if p]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extension(path: Path) -> str:
    if path.name.startswith(".") and "." not in path.name[1:]:
        return "[no extension]"
    return path.suffix.lower() or "[no extension]"


def decorator_name(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def python_symbols(path: Path) -> tuple[list[dict], list[dict]]:
    symbols: list[dict] = []
    parse_errors: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except Exception as exc:
        parse_errors.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
        return symbols, parse_errors

    def walk(body: list[ast.stmt], parents: list[str]) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = ".".join([*parents, node.name])
                decorators = [decorator_name(d) for d in node.decorator_list]
                symbols.append({
                    "path": str(path),
                    "language": "python",
                    "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                    "name": node.name,
                    "qualified_name": qual,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "decorators": decorators,
                })
                walk(node.body, [*parents, node.name])
            elif isinstance(node, ast.ClassDef):
                qual = ".".join([*parents, node.name])
                decorators = [decorator_name(d) for d in node.decorator_list]
                symbols.append({
                    "path": str(path),
                    "language": "python",
                    "kind": "class",
                    "name": node.name,
                    "qualified_name": qual,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "decorators": decorators,
                })
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        mqual = f"{qual}.{item.name}"
                        symbols.append({
                            "path": str(path),
                            "language": "python",
                            "kind": "async_method" if isinstance(item, ast.AsyncFunctionDef) else "method",
                            "name": item.name,
                            "qualified_name": mqual,
                            "line": item.lineno,
                            "end_line": getattr(item, "end_lineno", item.lineno),
                            "decorators": [decorator_name(d) for d in item.decorator_list],
                        })
                    elif isinstance(item, ast.ClassDef):
                        walk([item], [*parents, node.name])
    walk(tree.body, [])
    return symbols, parse_errors


JS_PATTERNS = [
    ("class", re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", re.M)),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", re.M)),
    ("arrow_function", re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^\n]*?\)|[A-Za-z_$][\w$]*)\s*=>", re.M)),
]


def js_ts_symbols(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    symbols = []
    for kind, pattern in JS_PATTERNS:
        for match in pattern.finditer(text):
            symbols.append({
                "path": str(path),
                "language": "typescript" if path.suffix.lower() in {".ts", ".tsx"} else "javascript",
                "kind": kind,
                "name": match.group(1),
                "qualified_name": match.group(1),
                "line": text.count("\n", 0, match.start()) + 1,
                "end_line": "",
                "decorators": [],
            })
    return symbols


def route_rows(symbols: list[dict]) -> list[dict]:
    rows = []
    route_re = re.compile(r"\.(get|post|put|patch|delete|options|head|websocket)\s*\(", re.I)
    for sym in symbols:
        for dec in sym.get("decorators", []):
            m = route_re.search(dec)
            if m:
                rows.append({
                    "path": sym["path"],
                    "qualified_name": sym["qualified_name"],
                    "line": sym["line"],
                    "method": m.group(1).upper(),
                    "decorator": dec,
                })
    return rows


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            cooked = dict(row)
            if isinstance(cooked.get("decorators"), list):
                cooked["decorators"] = " | ".join(cooked["decorators"])
            w.writerow({k: cooked.get(k, "") for k in fields})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = tracked_files()
    file_rows = []
    symbols: list[dict] = []
    parse_errors: list[dict] = []
    ext_counts: Counter[str] = Counter()
    total_bytes = 0

    for rel in files:
        p = ROOT / rel
        if not p.is_file():
            continue
        size = p.stat().st_size
        total_bytes += size
        ext_counts[extension(rel)] += 1
        file_rows.append({
            "path": str(rel),
            "size_bytes": size,
            "sha256": sha256(p),
            "extension": extension(rel),
        })
        suffix = rel.suffix.lower()
        if suffix == ".py":
            found, errors = python_symbols(rel)
            symbols.extend(found)
            parse_errors.extend(errors)
        elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
            symbols.extend(js_ts_symbols(rel))

    file_rows.sort(key=lambda r: r["path"])
    symbols.sort(key=lambda r: (r["path"], int(r["line"]), r["qualified_name"]))
    routes = route_rows(symbols)

    write_csv(OUT / "TRACKED_FILE_INVENTORY.csv", file_rows, ["path", "size_bytes", "sha256", "extension"])
    write_csv(OUT / "CODE_SYMBOL_INVENTORY.csv", symbols, ["path", "language", "kind", "name", "qualified_name", "line", "end_line", "decorators"])
    write_csv(OUT / "API_ROUTE_INVENTORY.csv", routes, ["path", "qualified_name", "line", "method", "decorator"])

    source_sha = git("rev-parse", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    symbol_kinds = Counter(s["kind"] for s in symbols)
    language_counts = Counter(s["language"] for s in symbols)

    summary = {
        "schema_version": 1,
        "branch": branch,
        "source_sha": source_sha,
        "tracked_file_count": len(file_rows),
        "tracked_bytes": total_bytes,
        "extensions": dict(sorted(ext_counts.items())),
        "code_symbol_count": len(symbols),
        "symbol_kinds": dict(sorted(symbol_kinds.items())),
        "symbol_languages": dict(sorted(language_counts.items())),
        "api_route_decorator_count": len(routes),
        "python_parse_errors": parse_errors,
        "external_8_file_pack_source_verified": False,
        "external_8_file_pack_included": False,
    }
    (OUT / "INVENTORY_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    overlap = [
        "# CK-NEXUS external-code overlap report",
        "",
        f"Base source SHA: `{source_sha}`",
        "",
        "The externally described eight-file pack was not present as file bytes in the ChatGPT conversation, Library, or this CK-NEXUS repository at inventory time. The entries below are therefore **NOT SOURCE-VERIFIED** and are not included in this package.",
        "",
        "| External filename | Claimed responsibility | Existing CK-NEXUS overlap | Status |",
        "|---|---|---|---|",
    ]
    for name, purpose, existing in EXTERNAL_PACK:
        overlap.append(f"| `{name}` | {purpose} | " + ", ".join(f"`{x}`" for x in existing) + " | NOT PROVIDED / NOT SOURCE-VERIFIED |")
    overlap.extend([
        "",
        "## Integration policy",
        "",
        "When the actual source pack is supplied, do not copy it directly over the runtime. First scan for secrets and dependencies, inventory schedulers/environment variables/functions, compare behavior against the modules above, and merge through CK-NEXUS governance boundaries. Token logic belongs behind Credential Broker/Vault; connector activation belongs behind Connector Fabric governance/security; Gmail monitoring belongs in Email Gateway/Observability; brain/self-upgrade behavior requires explicit policy/evidence/approval controls.",
        "",
    ])
    (OUT / "INTEGRATION_OVERLAP_REPORT.md").write_text("\n".join(overlap), encoding="utf-8")

    readme = f"""# CK-NEXUS Full-System Base Inventory\n\nExact source SHA: `{source_sha}`  \nBranch: `{branch}`\n\nGenerated files:\n- `TRACKED_FILE_INVENTORY.csv` — all Git-tracked files with size and SHA-256.\n- `CODE_SYMBOL_INVENTORY.csv` — Python functions/classes/methods plus best-effort JS/TS functions/classes.\n- `API_ROUTE_INVENTORY.csv` — Python route-like decorators found on callable symbols.\n- `INVENTORY_SUMMARY.json` — counts and parse status.\n- `INTEGRATION_OVERLAP_REPORT.md` — mapping for the externally described eight-file code pack.\n\nImportant: this is a full-system **base/source package**, not a Production Ready artifact. It does not claim the missing external eight-file pack is included or deployed.\n"""
    (OUT / "README_INVENTORY.md").write_text(readme, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
