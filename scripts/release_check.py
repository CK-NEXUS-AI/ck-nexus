from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    "data",
}
TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = {
    "OpenAI secret key": re.compile(r"\bsk-(?:proj-|admin-)?[A-Za-z0-9_-]{20,}\b"),
    "Stripe secret key": re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
REQUIRED_FILES = {
    ".env.example",
    ".gitignore",
    "DELIVERY_MANIFEST.txt",
    "Dockerfile",
    "README.md",
    "creator_app/api.py",
    "creator_app/runtime.py",
    "creator_app/web/index.html",
    "creator_app/web/app.js",
    "docs/ACCEPTANCE_CRITERIA.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/SECURITY_AUDIT.md",
    "docs/TEST_REPORT.md",
    "docs/UX_DESIGN_SYSTEM.md",
    "main.py",
    "pyproject.toml",
    "RELEASE_STATUS.md",
    "uv.lock",
}

COMMERCIAL_FILES = (
    "COMMERCIAL_LICENSE_TEMPLATE.md",
    "docs/SELLER_CHECKLIST.md",
)


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    required: bool = True


def run_command(name: str, command: list[str], *, required: bool = True) -> CheckResult:
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except FileNotFoundError:
        return CheckResult(name, False, "command not installed", required=required)
    except subprocess.TimeoutExpired:
        return CheckResult(name, False, "timed out", required=required)

    output = (process.stdout + process.stderr).strip().splitlines()
    summary = output[-1] if output else f"exit {process.returncode}"
    return CheckResult(name, process.returncode == 0, summary, required=required)


def scan_secrets() -> CheckResult:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.name == ".env.local" or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line} ({label})")

    if findings:
        return CheckResult("Secret scan", False, "; ".join(findings))
    return CheckResult("Secret scan", True, "no plaintext key pattern found")


def check_required_files() -> CheckResult:
    missing = sorted(item for item in REQUIRED_FILES if not (ROOT / item).exists())
    if missing:
        return CheckResult("Required files", False, "missing: " + ", ".join(missing))
    return CheckResult("Required files", True, f"{len(REQUIRED_FILES)} required files present")


def check_commercial_placeholders() -> CheckResult:
    files = [ROOT / item for item in COMMERCIAL_FILES]
    missing = [str(path.relative_to(ROOT)) for path in files if not path.exists()]
    if missing:
        return CheckResult(
            "Commercial package",
            False,
            "missing optional seller files: " + ", ".join(missing),
        )

    remaining = 0
    for path in files:
        try:
            remaining += path.read_text(encoding="utf-8").count("[ต้องการข้อมูลเพิ่ม]")
        except OSError as exc:
            return CheckResult(
                "Commercial package",
                False,
                f"could not read {path.relative_to(ROOT)}: {exc}",
            )
    return CheckResult(
        "Commercial package",
        remaining == 0,
        "complete" if remaining == 0 else f"{remaining} unresolved marker(s)",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="CK-NEXUS release gate")
    parser.add_argument(
        "--strict-commercial",
        action="store_true",
        help="fail while seller/legal placeholders remain",
    )
    args = parser.parse_args()

    results = [
        check_required_files(),
        scan_secrets(),
        run_command(
            "Python compile",
            [sys.executable, "-m", "compileall", "-q", "creator_app", "main.py"],
        ),
        run_command(
            "Trusted toolchain",
            [sys.executable, "scripts/gate_trusted_toolchain.py"],
        ),
        run_command(
            "Lock consistency",
            [sys.executable, "scripts/gate_lock_consistency.py"],
        ),
        run_command(
            "Dependency closure",
            [sys.executable, "scripts/gate_dependency_closure.py"],
        ),
        run_command(
            "Dependency preflight",
            [sys.executable, "scripts/dependency_preflight.py"],
        ),
        run_command("Test suite", [sys.executable, "-m", "pytest", "-q"]),
        run_command("Ruff", [sys.executable, "-m", "ruff", "check", "."]),
        run_command(
            "JavaScript syntax",
            ["node", "--check", "creator_app/web/app.js"],
            required=False,
        ),
        run_command(
            "Bandit",
            [
                sys.executable,
                "-m",
                "bandit",
                "-q",
                "-r",
                "creator_app",
                "services",
                "main.py",
            ],
        ),
        run_command(
            "Dependency audit",
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--cache-dir",
                str(Path(tempfile.gettempdir()) / "cknexus_pip_audit_cache"),
                "--progress-spinner",
                "off",
            ],
        ),
    ]
    commercial = check_commercial_placeholders()
    commercial.required = args.strict_commercial
    results.append(commercial)

    for result in results:
        icon = "PASS" if result.passed else ("FAIL" if result.required else "WARN")
        print(f"[{icon}] {result.name}: {result.detail}")

    return 1 if any(not item.passed and item.required for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
