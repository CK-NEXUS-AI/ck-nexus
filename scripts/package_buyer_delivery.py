from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DELIVERY_PREFIX = "CK-NEXUS-FULL-SOURCE-DELIVERY"

EXCLUDED_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx", ".log",
}
EXCLUDED_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "id_rsa", "id_ed25519", "credentials.json", "client_secret.json",
}
EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", "node_modules", "data", "dist", "build",
}
TEXT_SUFFIXES = {
    ".css", ".env", ".html", ".ini", ".js", ".json", ".md", ".ps1",
    ".py", ".sh", ".toml", ".txt", ".yaml", ".yml",
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_like_key": re.compile(r"\bsk-(?:proj-|admin-)?[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_-]{20,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}


def run(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def canonical_identity() -> tuple[str, str]:
    return run("git", "rev-parse", "HEAD"), run("git", "rev-parse", "HEAD^{tree}")


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [Path(item.decode("utf-8")) for item in raw.split(b"\0") if item]


def safe_tracked_file(rel: Path) -> bool:
    if rel.name in EXCLUDED_NAMES:
        return False
    if rel.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    return not (
        rel.name.startswith(".env") and rel.name != ".env.example"
    )


def copy_tracked_source(destination: Path) -> list[str]:
    copied: list[str] = []
    for rel in tracked_files():
        if not safe_tracked_file(rel):
            continue
        src = ROOT / rel
        if not src.is_file():
            continue
        dst = destination / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel.as_posix())
    return copied


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def scan_text_tree(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append({
                    "file": path.relative_to(root).as_posix(),
                    "type": label,
                })
    return findings


def write_sha256(root: Path, output: Path) -> int:
    rows: list[str] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == output:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(root).as_posix()}")
        count += 1
    write_text(output, "\n".join(rows))
    return count


def build_package(output_dir: Path, version: str) -> tuple[Path, str]:
    commit, tree = canonical_identity()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    delivery_name = f"{DELIVERY_PREFIX}-{version}"
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cknexus-buyer-delivery-") as td:
        root = Path(td) / delivery_name
        root.mkdir(parents=True)

        source_root = root / "02-SOURCE-CODE" / "repository"
        copied = copy_tracked_source(source_root)

        copy_if_exists(
            ROOT / "COMMERCIAL_LICENSE_TEMPLATE.md",
            root / "00-LEGAL" / "COMMERCIAL_LICENSE_TEMPLATE.md",
        )
        write_text(
            root / "00-LEGAL" / "LEGAL_REVIEW_REQUIRED.md",
            """# Legal review required

This delivery package does not execute a sale, assignment, warranty, or
production-readiness representation by itself.

Before transfer, the parties must complete and legally review:
- seller and buyer legal identities
- transaction model: assignment or license
- price, tax and payment terms
- governing law and dispute terms
- acceptance period and criteria
- warranty/support scope
- third-party exclusions
- exact artifact SHA-256 and commit identity

No AI-generated document should be treated as signed legal advice.
""",
        )

        for name in (
            "README.md",
            "INSTALL_GUIDE.md",
            "DELIVERY_MANIFEST.txt",
            "RELEASE_STATUS.md",
            "THIRD_PARTY_NOTICES.md",
            "CHANGELOG.md",
        ):
            copy_if_exists(ROOT / name, root / "01-SYSTEM-DOCS" / name)

        copy_if_exists(
            ROOT / "docs" / "RELEASE_CHECKLIST.md",
            root / "01-SYSTEM-DOCS" / "RELEASE_CHECKLIST.md",
        )

        for path in tracked_files():
            p = path.as_posix().lower()
            if not safe_tracked_file(path):
                continue
            src = ROOT / path
            if not src.is_file():
                continue
            if (
                "security" in p
                or "audit" in p
                or "evidence" in p
                or p.startswith("creator_app/privacy_firewall/")
                or p.startswith("creator_app/agnes/")
            ):
                copy_if_exists(src, root / "03-SECURITY-AND-VERIFICATION" / path)
            if p.startswith(".github/workflows/") or p.startswith("scripts/"):
                copy_if_exists(src, root / "04-AUTOMATION-AND-OPS" / path)
            if (
                p.startswith("creator_app/web/")
                or p.startswith("gateway/")
                or p.startswith("integrations/")
            ):
                copy_if_exists(src, root / "05-INTERFACES" / path)
            if p.startswith("docs/") or p.endswith(".md"):
                copy_if_exists(src, root / "06-DEVELOPER-DOCS" / path)

        for name in (
            "Dockerfile",
            "docker-compose.p0.yml",
            "docker-compose.prod.yml",
            "docker-compose.r9-r11.yml",
            ".env.example",
            "pyproject.toml",
            "uv.lock",
            "requirements-dev.txt",
            "start.sh",
            "start.ps1",
        ):
            copy_if_exists(ROOT / name, root / "07-INSTALL-AND-CONFIG" / name)

        copy_if_exists(
            ROOT / "THIRD_PARTY_NOTICES.md",
            root / "09-ASSETS-AND-LICENSES" / "THIRD_PARTY_NOTICES.md",
        )

        commit_history = run("git", "log", "--oneline", "--decorate", "-n", "500")
        branch_summary = run("git", "branch", "-a", "--no-color")
        write_text(
            root / "10-GIT-REFERENCE" / "commit-history.txt",
            commit_history,
        )
        write_text(
            root / "10-GIT-REFERENCE" / "branch-summary.txt",
            branch_summary,
        )
        write_text(
            root / "10-GIT-REFERENCE" / "canonical-commit-reference.txt",
            f"commit={commit}\ntree={tree}\n",
        )
        write_text(
            root / "10-GIT-REFERENCE" / "GIT_BUNDLE_NOT_INCLUDED.md",
            """# Git bundle not included by default

A full Git bundle can contain historical secrets even when the current tree is
clean. It must only be added after a dedicated full-history secret scan passes
and the seller explicitly approves that history for transfer.
""",
        )

        status = {
            "schema_version": 1,
            "generated_at_utc": stamp,
            "delivery_version": version,
            "source_commit": commit,
            "source_tree": tree,
            "tracked_source_files_copied": len(copied),
            "q10": "NOT_VERIFIED",
            "q11": "BLOCKED",
            "q12": "BLOCKED",
            "production": "NO-GO / NOT CERTIFIED",
            "commercial_classification": "SOURCE-CODE / DEVELOPMENT-OR-RELEASE-CANDIDATE",
            "git_bundle_included": False,
            "credentials_included": False,
            "personal_data_intended": False,
        }
        write_text(
            root / "01-SYSTEM-DOCS" / "DELIVERY_STATUS.json",
            json.dumps(status, indent=2, sort_keys=True),
        )
        write_text(
            root / "README-READ-FIRST.md",
            f"""# CK-NEXUS Buyer Delivery Package

Delivery identity:
- commit: {commit}
- tree: {tree}
- generated: {stamp}
- version: {version}

Important disclosure:
- Q10: NOT_VERIFIED
- Q11: BLOCKED
- Q12: BLOCKED
- Production: NO-GO / NOT CERTIFIED

This is a source-code / development-or-release-candidate delivery package.
It must not be represented as Production Ready or certified until the
applicable gates and independent human approvals are complete.

The package intentionally excludes runtime credentials, private keys,
production databases, personal user data, local caches, logs, and a full Git
bundle.
""",
        )

        findings = scan_text_tree(root)
        if findings:
            raise RuntimeError(
                "Secret-like material found in package: "
                + json.dumps(findings[:20], ensure_ascii=False)
            )

        checksum_count = write_sha256(
            root,
            root / "SHA256-CHECKSUM-ALL-FILES.txt",
        )

        manifest = {
            **status,
            "delivery_file_count_before_checksum": checksum_count,
            "secret_scan": "PASS",
        }
        write_text(
            root / "DELIVERY_MANIFEST.json",
            json.dumps(manifest, indent=2, sort_keys=True),
        )

        # Recompute after manifest creation so the checksum file covers it.
        write_sha256(root, root / "SHA256-CHECKSUM-ALL-FILES.txt")

        archive = output_dir / f"{delivery_name}.zip"
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(
            archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(root.parent))

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    write_text(
        archive.with_suffix(".zip.sha256"),
        f"{digest}  {archive.name}",
    )
    return archive, digest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a sanitized CK-NEXUS full-source buyer delivery ZIP."
    )
    parser.add_argument("--version", default="v0.2.0-buyer-candidate")
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=ROOT / "dist" / "buyer-delivery",
    )
    args = parser.parse_args()

    archive, digest = build_package(
        args.output_directory.resolve(),
        args.version,
    )
    print(f"archive={archive}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
