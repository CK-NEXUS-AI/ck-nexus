from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_NAME = "CK-NEXUS-Creator-Edition-v0.2.0"
ROOT_FILES = [
    ".dockerignore",
    ".env.example",
    ".gitignore",
    "CHANGELOG.md",
    "COMMERCIAL_LICENSE_TEMPLATE.md",
    "DELIVERY_MANIFEST.txt",
    "Dockerfile",
    "README.md",
    "RELEASE_STATUS.md",
    "THIRD_PARTY_NOTICES.md",
    "main.py",
    "pyproject.toml",
    "pytest.ini",
    "requirements-dev.txt",
    "start.ps1",
    "start.sh",
    "uv.lock",
]
SOURCE_DIRS = ["app", "creator_app", "docs", "scripts", "services", "tests"]
EXCLUDED_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".cache",
    ".tools",
    "__pycache__",
    "build",
    "data",
    "dist",
}
SECRET_PATTERNS = {
    "OpenAI secret key": re.compile(r"\bsk-(?:proj-|admin-)?[A-Za-z0-9_-]{20,}\b"),
    "Stripe secret key": re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
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


def ignored(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDED_NAMES or name.endswith(".pyc")}


def scan_text_files(bundle: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path.relative_to(bundle)} ({label})")
    return findings


def write_checksums(bundle: Path) -> None:
    lines: list[str] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.txt":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(bundle).as_posix()}")
    (bundle / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_archive(output_directory: Path) -> tuple[Path, str]:
    output_directory.mkdir(parents=True, exist_ok=True)
    archive_path = output_directory / f"{RELEASE_NAME}.zip"

    with tempfile.TemporaryDirectory(prefix="cknexus-release-") as temporary:
        bundle = Path(temporary) / RELEASE_NAME
        bundle.mkdir()

        for name in ROOT_FILES:
            source = ROOT / name
            if not source.is_file():
                raise FileNotFoundError(f"Required release file is missing: {name}")
            shutil.copy2(source, bundle / name)

        for name in SOURCE_DIRS:
            source = ROOT / name
            if not source.is_dir():
                raise FileNotFoundError(f"Required release directory is missing: {name}")
            shutil.copytree(source, bundle / name, ignore=ignored)

        packages = bundle / "packages"
        packages.mkdir()
        for pattern in ("*.whl", "*.tar.gz"):
            matches = sorted((ROOT / "dist").glob(pattern))
            if not matches:
                raise FileNotFoundError(f"No built package matching dist/{pattern}")
            for source in matches:
                shutil.copy2(source, packages / source.name)

        findings = scan_text_files(bundle)
        if findings:
            raise RuntimeError("Secret-like value found: " + "; ".join(findings))

        write_checksums(bundle)
        if archive_path.exists():
            archive_path.unlink()
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle.parent))

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = archive_path.with_suffix(".zip.sha256")
    checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    return archive_path, digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the CK-NEXUS source-sale delivery ZIP")
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=ROOT.parent,
        help="Directory for the ZIP and its SHA-256 sidecar",
    )
    args = parser.parse_args()
    archive, digest = build_archive(args.output_directory.resolve())
    print(f"archive: {archive}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
